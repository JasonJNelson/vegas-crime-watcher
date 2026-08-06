#!/usr/bin/env python3
"""
Vegas Crime Watcher — pure Python (stdlib only)

Interactive Las Vegas crime map + live-style feed.
Integrates LVMPD ArcGIS Calls-for-Service data with seed fallback.
Zero external dependencies.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "templates" / "index.html"

# LVMPD ArcGIS Feature Service (public, no API key)
ARCGIS_QUERY_URL = (
    "https://services.arcgis.com/jjSk6t82vIntwDbs/ArcGIS/rest/services/"
    "LVMPD_Calls_For_Service_All/FeatureServer/0/query"
)

# How often to poll ArcGIS (seconds)
POLL_INTERVAL_SEC = 600  # 10 minutes
# How many recent CFS records to pull per poll
POLL_LIMIT = 150

# ---------------------------------------------------------------------------
# Seed crime data (fallback when ArcGIS is unreachable)
# ---------------------------------------------------------------------------

SEED_CRIMES: list[dict] = [
    {
        "id": 1,
        "type": "homicide",
        "title": "Good Samaritan fatally shot trying to stop flower robbery",
        "address": "100 block Upland Blvd near Jones Blvd",
        "lat": 36.1595,
        "lng": -115.2238,
        "time": "2026-07-30 17:00",
        "description": (
            "Man intervened when suspect robbed a woman selling flowers. "
            "Suspect (Rodger Harrison, 28) arrested nearby. "
            "Charges: open murder, robbery, CCW."
        ),
        "source": "seed",
    },
    {
        "id": 2,
        "type": "shooting",
        "title": "Officer-involved shooting at Walmart — Boulder Hwy",
        "address": "5100 block Boulder Highway",
        "lat": 36.1002,
        "lng": -115.0615,
        "time": "2026-07-21 06:00",
        "description": (
            "Physical altercation inside business escalated. Suspect exited "
            "with firearm; officer discharged. Suspect deceased; second male "
            "critical. 8th OIS of 2026."
        ),
        "source": "seed",
    },
    {
        "id": 3,
        "type": "homicide",
        "title": "Gang-related shooting near Hollywood Regional Park",
        "address": "1500 block S Hollywood Blvd",
        "lat": 36.1520,
        "lng": -115.0450,
        "time": "2026-07-18 14:30",
        "description": (
            "Carlos Valenzuela, 20, killed. Cousins Jayden Torres (19) and "
            "Kassandra Orozco (16) arrested on open murder charges."
        ),
        "source": "seed",
    },
    {
        "id": 4,
        "type": "robbery",
        "title": "Deadly parking-garage robbery spree (Strip area)",
        "address": "Fashion Show mall / Strip parking structures",
        "lat": 36.1275,
        "lng": -115.1715,
        "time": "2026-07-30 (court)",
        "description": (
            "Jordan Ruby pleaded guilty in high-profile robbery spree that "
            "killed two victims, including a senior."
        ),
        "source": "seed",
    },
    {
        "id": 5,
        "type": "homicide",
        "title": "Murder-suicide investigated",
        "address": "Las Vegas valley (LVMPD)",
        "lat": 36.1699,
        "lng": -115.1398,
        "time": "2026-07-21",
        "description": (
            "LVMPD investigating murder-suicide. Details limited pending "
            "investigation."
        ),
        "source": "seed",
    },
    {
        "id": 6,
        "type": "assault",
        "title": "Shooting leaves one dead — update, additional suspect arrested",
        "address": "West Las Vegas area",
        "lat": 36.1750,
        "lng": -115.2100,
        "time": "2026-07-27",
        "description": (
            "Additional suspect arrested in connection with earlier fatal "
            "shooting."
        ),
        "source": "seed",
    },
    {
        "id": 7,
        "type": "theft",
        "title": "Vehicle theft cluster — Boulder Falls area",
        "address": "5800 Boulder Falls St",
        "lat": 36.0550,
        "lng": -115.0800,
        "time": "2026-07-28",
        "description": (
            "Multiple vehicle theft reports in southeast valley neighborhoods."
        ),
        "source": "seed",
    },
    {
        "id": 8,
        "type": "burglary",
        "title": "Residential burglary — N Buffalo Dr",
        "address": "2600 N Buffalo Dr",
        "lat": 36.1950,
        "lng": -115.2600,
        "time": "2026-07-25",
        "description": "Breaking & entering reported; investigation ongoing.",
        "source": "seed",
    },
    {
        "id": 9,
        "type": "robbery",
        "title": "Attempted business robbery — Flamingo / Jones area",
        "address": "Near Jones & Flamingo",
        "lat": 36.1150,
        "lng": -115.2250,
        "time": "2026-07-22",
        "description": (
            "Suspect fled after attempting to rob business. Public asked for tips."
        ),
        "source": "seed",
    },
    {
        "id": 10,
        "type": "shooting",
        "title": "Shooting investigation — NE Las Vegas business",
        "address": "4900 block E Craig Rd near Nellis",
        "lat": 36.2400,
        "lng": -115.0600,
        "time": "2026-06-19 (still active case)",
        "description": (
            "Man killed, woman injured after verbal altercation escalated to "
            "gunfire. Suspect fled."
        ),
        "source": "seed",
    },
    {
        "id": 11,
        "type": "vandalism",
        "title": "Property damage / vandalism",
        "address": "7500 Hickam Ave",
        "lat": 36.0800,
        "lng": -115.2700,
        "time": "2026-07-15",
        "description": "Destruction/damage of property reported.",
        "source": "seed",
    },
    {
        "id": 12,
        "type": "theft",
        "title": "Larceny — Tropicana corridor",
        "address": "6100 W Tropicana Ave",
        "lat": 36.1000,
        "lng": -115.2300,
        "time": "2026-07-14",
        "description": "All other larceny reported.",
        "source": "seed",
    },
    {
        "id": 13,
        "type": "assault",
        "title": "Aggravated assault — Downtown area",
        "address": "Near Fremont St / Downtown",
        "lat": 36.1699,
        "lng": -115.1398,
        "time": "2026-07-26",
        "description": "Assault reported; suspect description released by LVMPD.",
        "source": "seed",
    },
    {
        "id": 14,
        "type": "burglary",
        "title": "Burglary — S Maryland Pkwy",
        "address": "4000 S Maryland Pkwy",
        "lat": 36.1200,
        "lng": -115.1400,
        "time": "2026-07-12",
        "description": "Commercial burglary under investigation.",
        "source": "seed",
    },
    {
        "id": 15,
        "type": "other",
        "title": "Vehicle vs pedestrian — fatal collision",
        "address": "W Sahara Ave at S Torrey Pines",
        "lat": 36.1440,
        "lng": -115.2700,
        "time": "2026-07-23",
        "description": "Fatal traffic collision investigated as Fatal #67.",
        "source": "seed",
    },
]

LIVE_CRIMES: list[dict] = list(SEED_CRIMES)
_next_id = 1000
_lock = threading.Lock()
_data_source = "seed"  # "seed" | "lvmpd-arcgis" | "mixed"
_last_poll_ok: datetime | None = None
_last_poll_error: str | None = None
_poller_started = False

NEW_CRIME_POOL = [
    {
        "type": "theft",
        "title": "Catalytic converter theft reported",
        "address": "3200 block E Tropicana Ave",
        "lat": 36.1005,
        "lng": -115.1050,
        "description": "Vehicle parts theft. Suspect vehicle described as dark sedan.",
    },
    {
        "type": "assault",
        "title": "Simple assault outside casino",
        "address": "Near Las Vegas Blvd / Flamingo",
        "lat": 36.1147,
        "lng": -115.1728,
        "description": (
            "Altercation outside property; one transported with "
            "non-life-threatening injuries."
        ),
    },
    {
        "type": "robbery",
        "title": "Strong-arm robbery — pedestrian",
        "address": "1600 block E Charleston Blvd",
        "lat": 36.1590,
        "lng": -115.1300,
        "description": (
            "Victim approached from behind; phone and wallet taken. "
            "Suspect fled on foot."
        ),
    },
    {
        "type": "burglary",
        "title": "Garage burglary — Summerlin area",
        "address": "Near Far Hills / Town Center",
        "lat": 36.1650,
        "lng": -115.3200,
        "description": "Tools and bicycle taken from open garage overnight.",
    },
    {
        "type": "shooting",
        "title": "Shots fired call — no victims located",
        "address": "2800 block N Las Vegas Blvd",
        "lat": 36.2050,
        "lng": -115.1200,
        "description": (
            "Multiple 911 calls of gunfire. Officers canvassed; no injuries "
            "found. Shell casings recovered."
        ),
    },
]

TYPE_MAP = [
    ("HOMICIDE", "homicide"),
    ("MURDER", "homicide"),
    ("SHOOTING", "shooting"),
    ("GUNSHOT", "shooting"),
    ("ROBBERY", "robbery"),
    ("ASSAULT", "assault"),
    ("BATTERY", "assault"),
    ("FIGHT", "assault"),
    ("BURGLARY", "burglary"),
    ("B&E", "burglary"),
    ("LARCENY", "theft"),
    ("THEFT", "theft"),
    ("STOLEN", "theft"),
    ("VEHICLE THEFT", "theft"),
    ("VANDALISM", "vandalism"),
    ("GRAFFITI", "vandalism"),
]


def classify_type(raw: str) -> str:
    upper = (raw or "").upper()
    for key, mapped in TYPE_MAP:
        if key in upper:
            return mapped
    return "other"


def add_simulated_crime() -> dict:
    global _next_id
    template = random.choice(NEW_CRIME_POOL)
    now = datetime.now()
    with _lock:
        crime = {
            "id": _next_id,
            **template,
            "time": now.strftime("%Y-%m-%d %H:%M"),
            "source": "simulated",
        }
        _next_id += 1
        LIVE_CRIMES.insert(0, crime)
    return crime


def fetch_lvmpd_cfs(limit: int = POLL_LIMIT) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "orderByFields": "OBJECTID DESC",
        "resultRecordCount": str(limit),
        "f": "geojson",
    }
    url = ARCGIS_QUERY_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VegasCrimeWatcher/1.0 (educational demo)"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    features = payload.get("features") or []
    crimes: list[dict] = []

    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        lng, lat = (coords + [None, None])[:2]

        incident_id = (
            props.get("incidentnumber")
            or props.get("IncidentNumber")
            or props.get("EVENT_NUMBER")
            or props.get("OBJECTID")
        )
        classification = (
            props.get("Classification")
            or props.get("classification")
            or props.get("Type")
            or props.get("type")
            or props.get("CallType")
            or props.get("FinalType")
            or ""
        )
        address = (
            props.get("address")
            or props.get("Address")
            or props.get("LOCATION")
            or props.get("Location")
            or props.get("BlockAddress")
            or ""
        )
        time_raw = (
            props.get("timedispatch")
            or props.get("TimeDispatch")
            or props.get("CreateDate")
            or props.get("DATE")
            or props.get("CallDate")
            or ""
        )
        if isinstance(time_raw, (int, float)) and time_raw > 1e11:
            try:
                time_str = datetime.utcfromtimestamp(time_raw / 1000).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except (OSError, ValueError, OverflowError):
                time_str = str(time_raw)
        else:
            time_str = str(time_raw) if time_raw else ""

        if lat is None or lng is None:
            lat = props.get("Latitude") or props.get("lat") or props.get("Y")
            lng = props.get("Longitude") or props.get("lng") or props.get("X")

        try:
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat_f, lng_f = None, None

        if lat_f is None or lng_f is None:
            continue
        if not (35.8 < lat_f < 36.5 and -115.6 < lng_f < -114.7):
            continue

        ctype = classify_type(str(classification))
        title = str(classification).strip() or "Call for service"

        crimes.append(
            {
                "id": f"lvmpd-{incident_id}",
                "type": ctype,
                "title": title,
                "address": str(address).strip() or "Las Vegas area",
                "lat": round(lat_f, 5),
                "lng": round(lng_f, 5),
                "time": time_str,
                "description": f"LVMPD Call for Service: {title}",
                "source": "lvmpd-arcgis",
            }
        )

    return crimes


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
        print(
            f"[{_last_poll_ok.strftime('%H:%M:%S')}] "
            f"ArcGIS poll OK — {len(fetched)} records, {added} new"
        )
    except urllib.error.HTTPError as e:
        _last_poll_error = f"HTTP {e.code}: {e.reason}"
        print(f"[poll] ArcGIS HTTP error: {_last_poll_error}")
    except urllib.error.URLError as e:
        _last_poll_error = f"URL error: {e.reason}"
        print(f"[poll] ArcGIS URL error: {_last_poll_error}")
    except Exception as e:  # noqa: BLE001
        _last_poll_error = str(e)
        print(f"[poll] ArcGIS error: {_last_poll_error}")


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
    t = threading.Thread(target=_poller_loop, name="lvmpd-poller", daemon=True)
    t.start()
    print(
        f"LVMPD ArcGIS poller started "
        f"(every {POLL_INTERVAL_SEC}s, limit={POLL_LIMIT})"
    )


def render_html() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    with _lock:
        crimes_json = json.dumps(LIVE_CRIMES)
    return template.replace("__CRIMES_JSON__", crimes_json)


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

        elif path == "/api/health":
            with _lock:
                count = len(LIVE_CRIMES)
            self._send_json(
                {
                    "status": "ok",
                    "crimes": count,
                    "source": _data_source,
                    "last_poll_ok": (
                        _last_poll_ok.isoformat(timespec="seconds")
                        if _last_poll_ok
                        else None
                    ),
                    "last_poll_error": _last_poll_error,
                    "poll_interval_sec": POLL_INTERVAL_SEC,
                }
            )

        elif path == "/api/source":
            self._send_json(
                {
                    "source": _data_source,
                    "last_poll_ok": (
                        _last_poll_ok.isoformat(timespec="seconds")
                        if _last_poll_ok
                        else None
                    ),
                    "last_poll_error": _last_poll_error,
                    "endpoint": ARCGIS_QUERY_URL,
                }
            )

        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/simulate":
            crime = add_simulated_crime()
            self._send_json(crime, status=201)
        elif path == "/api/poll":
            poll_once()
            with _lock:
                count = len(LIVE_CRIMES)
            self._send_json(
                {
                    "ok": _last_poll_error is None,
                    "source": _data_source,
                    "crimes": count,
                    "error": _last_poll_error,
                }
            )
        else:
            self.send_error(404, "Not Found")


def run(host: str | None = None, port: int | None = None) -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

    # Railway / cloud: bind 0.0.0.0 and use $PORT
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", "8080"))

    start_poller()

    server = HTTPServer((host, port), CrimeHandler)
    print(f"🚨 Vegas Crime Watcher running at http://{host}:{port}")
    print("   Endpoints:")
    print("     GET  /              → full interactive UI")
    print("     GET  /api/crimes    → JSON crime list")
    print("     GET  /api/health    → health + poll status")
    print("     GET  /api/source    → data source info")
    print("     POST /api/simulate  → add simulated incident")
    print("     POST /api/poll      → force ArcGIS poll now")
    print("   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    run()
