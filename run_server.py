#!/usr/bin/env python3
"""Vegas Crime Watcher — long-running server (local / Railway / Docker)."""
from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from lib.core import (
    ARCGIS_QUERY_URL,
    POLL_INTERVAL_SEC,
    POLL_LIMIT,
    SEED_CRIMES,
    NEW_CRIME_POOL,
    classify_type,
    fetch_lvmpd_cfs,
)

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "templates" / "index.html"

LIVE_CRIMES: list[dict] = list(SEED_CRIMES)
_next_id = 1000
_lock = threading.Lock()
_data_source = "seed"
_last_poll_ok: datetime | None = None
_last_poll_error: str | None = None
_poller_started = False


def add_simulated_crime() -> dict:
    global _next_id
    template = random.choice(NEW_CRIME_POOL)
    now = datetime.now()
    with _lock:
        crime = {"id": _next_id, **template, "time": now.strftime("%Y-%m-%d %H:%M"), "source": "simulated"}
        _next_id += 1
        LIVE_CRIMES.insert(0, crime)
    return crime


def merge_live_crimes(incoming: list[dict]) -> int:
    global _data_source
    with _lock:
        existing_ids = {str(c.get("id")) for c in LIVE_CRIMES}
        added = 0
        for crime in incoming:
            cid = str(crime.get("id"))
            if cid in existing_ids:
                continue
            LIVE_CRIMES.insert(0, crime)
            existing_ids.add(cid)
            added += 1
        if len(LIVE_CRIMES) > 500:
            del LIVE_CRIMES[500:]
        sources = {c.get("source") for c in LIVE_CRIMES}
        if "lvmpd-arcgis" in sources and "seed" in sources:
            _data_source = "mixed"
        elif "lvmpd-arcgis" in sources:
            _data_source = "lvmpd-arcgis"
        else:
            _data_source = "seed"
    return added


def poll_once() -> None:
    global _last_poll_ok, _last_poll_error
    try:
        fetched = fetch_lvmpd_cfs()
        added = merge_live_crimes(fetched)
        _last_poll_ok = datetime.now()
        _last_poll_error = None
        print(f"[{_last_poll_ok.strftime('%H:%M:%S')}] ArcGIS poll OK — {len(fetched)} records, {added} new")
    except urllib.error.HTTPError as e:
        _last_poll_error = f"HTTP {e.code}: {e.reason}"
        print(f"[poll] {_last_poll_error}")
    except urllib.error.URLError as e:
        _last_poll_error = f"URL error: {e.reason}"
        print(f"[poll] {_last_poll_error}")
    except Exception as e:  # noqa: BLE001
        _last_poll_error = str(e)
        print(f"[poll] {_last_poll_error}")


def _poller_loop() -> None:
    time.sleep(2)
    while True:
        poll_once()
        time.sleep(POLL_INTERVAL_SEC)


def start_poller() -> None:
    global _poller_started
    if _poller_started:
        return
    _poller_started = True
    threading.Thread(target=_poller_loop, name="lvmpd-poller", daemon=True).start()
    print(f"LVMPD ArcGIS poller started (every {POLL_INTERVAL_SEC}s)")


def render_html() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    with _lock:
        crimes_json = json.dumps(LIVE_CRIMES)
    return template.replace("__CRIMES_JSON__", crimes_json)


def health_payload() -> dict:
    with _lock:
        count = len(LIVE_CRIMES)
    return {
        "status": "ok",
        "service": "vegas-crime-watcher",
        "crimes": count,
        "source": _data_source,
        "last_poll_ok": (_last_poll_ok.isoformat(timespec="seconds") if _last_poll_ok else None),
        "last_poll_error": _last_poll_error,
        "poll_interval_sec": POLL_INTERVAL_SEC,
    }


class CrimeHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = render_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/crimes":
            with _lock:
                self._send_json(LIVE_CRIMES)
        elif path in ("/health", "/healthz", "/api/health"):
            self._send_json(health_payload())
        elif path == "/api/source":
            self._send_json({
                "source": _data_source,
                "last_poll_ok": (_last_poll_ok.isoformat(timespec="seconds") if _last_poll_ok else None),
                "last_poll_error": _last_poll_error,
                "endpoint": ARCGIS_QUERY_URL,
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/simulate":
            self._send_json(add_simulated_crime(), status=201)
        elif path == "/api/poll":
            poll_once()
            with _lock:
                count = len(LIVE_CRIMES)
            self._send_json({
                "ok": _last_poll_error is None,
                "source": _data_source,
                "crimes": count,
                "error": _last_poll_error,
            })
        else:
            self.send_error(404, "Not Found")


def _resolve_bind(host: str | None, port: int | None) -> tuple[str, int]:
    env_port = os.environ.get("PORT")
    allow_public = os.environ.get("ALLOW_PUBLIC", "").strip().lower() in {"1", "true", "yes", "on"}
    if port is None:
        port = int(env_port) if env_port else 8080
    if host is not None:
        return host, port
    env_host = os.environ.get("HOST")
    if env_host:
        return env_host, port
    if allow_public or env_port is not None:
        return "0.0.0.0", port
    return "127.0.0.1", port


def run(host: str | None = None, port: int | None = None) -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")
    host, port = _resolve_bind(host, port)
    start_poller()
    server = HTTPServer((host, port), CrimeHandler)
    scope = "localhost only" if host in ("127.0.0.1", "localhost") else "all interfaces"
    print(f"Vegas Crime Watcher at http://{host}:{port}  ({scope})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    run()
