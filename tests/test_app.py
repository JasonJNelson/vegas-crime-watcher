"""Unit tests for Vegas Crime Watcher (stdlib only)."""

from __future__ import annotations

import ast
import json
import pathlib
import unittest
from unittest import mock

# Project root is parent of tests/
ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

import app  # noqa: E402


class TestSyntax(unittest.TestCase):
    def test_app_parses(self) -> None:
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        ast.parse(src)


class TestClassify(unittest.TestCase):
    def test_known_types(self) -> None:
        self.assertEqual(app.classify_type("ASSAULT/BATTERY"), "assault")
        self.assertEqual(app.classify_type("Stolen Vehicle"), "theft")
        self.assertEqual(app.classify_type("BURGLARY RESIDENTIAL"), "burglary")
        self.assertEqual(app.classify_type("Robbery"), "robbery")
        self.assertEqual(app.classify_type("Homicide"), "homicide")
        self.assertEqual(app.classify_type("Shots Fired / Shooting"), "shooting")
        self.assertEqual(app.classify_type("Graffiti"), "vandalism")

    def test_unknown(self) -> None:
        self.assertEqual(app.classify_type("Traffic Accident"), "other")
        self.assertEqual(app.classify_type(""), "other")


class TestSeedData(unittest.TestCase):
    def test_seed_count(self) -> None:
        self.assertEqual(len(app.SEED_CRIMES), 15)

    def test_seed_shape(self) -> None:
        required = {"id", "type", "title", "address", "lat", "lng", "time", "description"}
        for c in app.SEED_CRIMES:
            self.assertTrue(required.issubset(c.keys()), msg=c)
            self.assertIsInstance(c["lat"], float)
            self.assertIsInstance(c["lng"], float)


class TestSimulate(unittest.TestCase):
    def test_add_simulated(self) -> None:
        before = len(app.LIVE_CRIMES)
        crime = app.add_simulated_crime()
        self.assertEqual(crime["source"], "simulated")
        self.assertIn("id", crime)
        self.assertGreaterEqual(len(app.LIVE_CRIMES), before + 1)


class TestMerge(unittest.TestCase):
    def test_dedupe(self) -> None:
        incoming = [
            {
                "id": "lvmpd-test-1",
                "type": "theft",
                "title": "Test",
                "address": "Somewhere",
                "lat": 36.17,
                "lng": -115.14,
                "time": "2026-08-01 12:00",
                "description": "test",
                "source": "lvmpd-arcgis",
            }
        ]
        added1 = app.merge_live_crimes(incoming)
        added2 = app.merge_live_crimes(incoming)
        self.assertEqual(added1, 1)
        self.assertEqual(added2, 0)


class TestFetchNormalization(unittest.TestCase):
    def test_fetch_parses_geojson(self) -> None:
        fake = {
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-115.14, 36.17]},
                    "properties": {
                        "incidentnumber": "LLV999",
                        "Classification": "Assault/Battery",
                        "address": "100 Fremont St",
                        "timedispatch": "2026-08-01 10:00",
                    },
                }
            ]
        }
        payload = json.dumps(fake).encode("utf-8")

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return payload

        with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
            rows = app.fetch_lvmpd_cfs(limit=5)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["type"], "assault")
        self.assertEqual(rows[0]["id"], "lvmpd-LLV999")
        self.assertEqual(rows[0]["source"], "lvmpd-arcgis")
        self.assertAlmostEqual(rows[0]["lat"], 36.17, places=2)


class TestTemplate(unittest.TestCase):
    def test_template_exists(self) -> None:
        self.assertTrue(app.TEMPLATE_PATH.exists())

    def test_render_html(self) -> None:
        html = app.render_html()
        self.assertIn("Vegas Crime Watcher", html)
        self.assertIn("leaflet", html)
        self.assertIn("light_all", html)
        self.assertIn("let crimes =", html)


if __name__ == "__main__":
    unittest.main()
