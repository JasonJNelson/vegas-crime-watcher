"""Vercel serverless: POST /api/simulate (stateless)."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        template = random.choice(app.NEW_CRIME_POOL)
        crime = {
            "id": f"sim-{int(datetime.now().timestamp())}-{random.randint(100,999)}",
            **template,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "simulated",
        }
        body = json.dumps(crime).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_response(405)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A002
        return
