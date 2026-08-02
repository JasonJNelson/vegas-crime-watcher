# Vegas Crime Watcher

Complete working interactive Las Vegas crime map and live-style incident feed.

**Pure Python — zero external dependencies** (stdlib only).

## Features

- Interactive dark Leaflet map centered on Las Vegas
- Color-coded markers by crime type (homicide, shooting, robbery, assault, burglary, theft, vandalism)
- Filterable crime feed
- Live simulation (`POST /api/simulate`)
- Login / Subscribe modals (demo)
- Pricing tiers UI ($0 / $9.99 / $29.99)
- REST API:
  - `GET /` — full web UI
  - `GET /api/crimes` — current crime list (JSON)
  - `POST /api/simulate` — add a new simulated incident
  - `GET /api/health` — health check

## Requirements

- Python 3.9+

## Run

```bash
python app.py
```

Open **http://127.0.0.1:8080**

## Project layout

```
vegas-crime-watcher/
├── app.py                  # server + crime data + API
├── templates/
│   └── index.html          # full interactive front-end
├── README.md
└── requirements.txt
```

## Data notes

Incident data is illustrative and drawn from public LVMPD press releases and local reporting (July 2026).  
This is a **demo / educational** project — not an official police product.

Always call **911** for emergencies.

## License

MIT
