# Vegas Crime Watcher

[![CI](https://github.com/JasonJNelson/vegas-crime-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/JasonJNelson/vegas-crime-watcher/actions/workflows/ci.yml)

Complete working interactive Las Vegas crime map and live-style incident feed.

**Pure Python — zero external dependencies** (stdlib only).

## Features

- Interactive Leaflet map centered on Las Vegas (light basemap)
- Color-coded markers by crime type
- Filterable crime feed
- **LVMPD ArcGIS live poller** — pulls real Calls-for-Service data
- Seed data fallback when ArcGIS is unreachable
- Login / Subscribe modals (demo)
- Pricing tiers UI
- REST API

## Data sources

| Source | Description |
|--------|-------------|
| **LVMPD ArcGIS** | Public Feature Service: Calls for Service (CAD). Polled every 10 minutes. |
| **Seed** | Illustrative incidents from public LVMPD press / local reporting (July 2026) |
| **Simulated** | Demo "+" button / `POST /api/simulate` |

CFS records are **calls for service**, not always confirmed crimes. The app maps classifications into homicide / shooting / robbery / assault / burglary / theft / vandalism / other.

## Run

```bash
python app.py
```

Open **http://127.0.0.1:8080**

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Full interactive UI |
| GET | `/api/crimes` | Current crime list (JSON) |
| GET | `/api/health` | Health + poll status |
| GET | `/api/source` | Data source + ArcGIS endpoint |
| POST | `/api/simulate` | Add a simulated incident |
| POST | `/api/poll` | Force an ArcGIS poll now |

## Project layout

```
vegas-crime-watcher/
├── app.py                  # server + ArcGIS poller + seed data
├── templates/
│   └── index.html          # interactive front-end
├── tests/
│   └── test_app.py         # unit tests
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI
├── README.md
└── requirements.txt
```

## Config (in `app.py`)

- `POLL_INTERVAL_SEC` — default `600` (10 min)
- `POLL_LIMIT` — max CFS records per poll (default `150`)
- `ARCGIS_QUERY_URL` — LVMPD FeatureServer query endpoint

## CI

GitHub Actions runs on every push and PR to `main`:

- Syntax check (`py_compile`)
- Unit tests (`python -m unittest`)
- Smoke test of the HTTP server
- Optional live ArcGIS poll (non-blocking)

```bash
python -m unittest discover -s tests -v
```

## Notes

- This is a **demo / educational** project — not an official police product.
- LVMPD does not guarantee completeness of open data.
- Always call **911** for emergencies.

## License

MIT
