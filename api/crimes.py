"""Vercel serverless: GET /api/crimes"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.core import SEED_CRIMES, fetch_lvmpd_cfs  # noqa: E402


def _load_crimes() -> list[dict]:
    crimes = list(SEED_CRIMES)
    try:
        live = fetch_lvmpd_cfs(limit=80)
        seen = {str(c.get("id")) for c in crimes}
        for c in live:
            cid = str(c.get("id"))
            if cid not in seen:
                crimes.insert(0, c)
                seen.add(cid)
    except Exception:
        pass
    return crimes[:400]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(_load_crimes()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "s-maxage=120, stale-while-revalidate=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        return
