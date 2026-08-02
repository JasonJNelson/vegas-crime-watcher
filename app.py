#!/usr/bin/env python3
"""
Vegas Crime Watcher — pure Python (stdlib only)

Complete working interactive Las Vegas crime map + live-style feed.
Zero external dependencies.
"""

from __future__ import annotations

import json
import random
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "templates" / "index.html"

# ---------------------------------------------------------------------------
# Crime data (seeded from public LVMPD / news reports – July 2026)
# ---------------------------------------------------------------------------

CRIMES: list[dict] = [
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
    },
]

LIVE_CRIMES: list[dict] = list(CRIMES)
_next_id = 100
_lock = threading.Lock()

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


def add_simulated_crime() -> dict:
    """Add a new simulated incident to the live feed."""
    global _next_id
    template = random.choice(NEW_CRIME_POOL)
    now = datetime.now()
    with _lock:
        crime = {
            "id": _next_id,
            **template,
            "time": now.strftime("%Y-%m-%d %H:%M"),
        }
        _next_id += 1
        LIVE_CRIMES.insert(0, crime)
    return crime


def render_html() -> str:
    """Load the HTML template and inject current crime data."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    with _lock:
        crimes_json = json.dumps(LIVE_CRIMES)
    return template.replace("__CRIMES_JSON__", crimes_json)


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

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
            self._send_json({"status": "ok", "crimes": len(LIVE_CRIMES)})

        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/simulate":
            crime = add_simulated_crime()
            self._send_json(crime, status=201)
        else:
            self.send_error(404, "Not Found")


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

    server = HTTPServer((host, port), CrimeHandler)
    print(f"🚨 Vegas Crime Watcher running at http://{host}:{port}")
    print("   Endpoints:")
    print("     GET  /              → full interactive UI")
    print("     GET  /api/crimes    → JSON crime list")
    print("     POST /api/simulate  → add simulated incident")
    print("     GET  /api/health    → health check")
    print("   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    run()
