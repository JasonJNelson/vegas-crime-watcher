"""Vercel serverless: POST /api/simulate"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.core import random_simulated  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.dumps(random_simulated()).encode("utf-8")
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
