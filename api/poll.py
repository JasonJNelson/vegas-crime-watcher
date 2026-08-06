"""
Vercel serverless: GET/POST /api/poll

Triggered by Vercel Cron (and manually). Fetches LVMPD ArcGIS CFS on demand.
Optional: set CRON_SECRET env → require Authorization: Bearer <secret>
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def _authorized(headers) -> bool:
    secret = os.environ.get("CRON_SECRET", "").strip()
    if not secret:
        return True
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if auth == f"Bearer {secret}":
        return True
    if headers.get("x-vercel-cron") or headers.get("X-Vercel-Cron"):
        return True
    return False


def _run_poll() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    try:
        fetched = app.fetch_lvmpd_cfs(limit=100)
        return {
            "ok": True,
            "fetched": len(fetched),
            "started": started,
            "finished": datetime.now(timezone.utc).isoformat(),
            "sample": (fetched[0].get("title") if fetched else None),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(e),
            "started": started,
            "finished": datetime.now(timezone.utc).isoformat(),
        }


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not _authorized(self.headers):
            self._json(401, {"ok": False, "error": "unauthorized"})
            return
        self._json(200, _run_poll())

    def do_POST(self):
        self.do_GET()

    def log_message(self, format, *args):  # noqa: A002
        return
