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

CFS records are **calls for service**, not always confirmed crimes.

## Run (local)

```bash
python app.py
# → http://127.0.0.1:8080
```

## Docker

Railway uses the `Dockerfile` when present (`railway.toml` sets `builder = "DOCKERFILE"`).

### Build & run locally

```bash
docker build -t vegas-crime-watcher .
docker run --rm -p 8080:8080 -e PORT=8080 vegas-crime-watcher
# → http://localhost:8080
```

Or with Compose:

```bash
docker compose up --build
```

Image notes:

- Base: `python:3.12-slim-bookworm`
- No `pip install` (stdlib only)
- Non-root user `appuser`
- `HEALTHCHECK` → `/api/health`
- Listens on `0.0.0.0:$PORT`

### Railway + Docker

1. Push this repo (Dockerfile is on `main`).
2. **New Project → Deploy from GitHub** → select the repo.
3. Railway builds from `Dockerfile`.
4. **Settings → Networking → Generate Domain**.

If it still uses Nixpacks, set:
`RAILWAY_DOCKERFILE_PATH=Dockerfile`
or **Settings → Build → Builder → Dockerfile**.

## Deploy (Railway)

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Select **JasonJNelson/vegas-crime-watcher**.
3. App binds to `0.0.0.0:$PORT` (Railway injects `PORT`).
4. Generate a public domain under **Networking**.
5. Health: `GET /api/health`

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
├── app.py
├── templates/index.html
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── railway.toml
├── Procfile
├── tests/
└── .github/workflows/ci.yml
```

## CI

```bash
python -m unittest discover -s tests -v
```

## Notes

- Demo / educational — not an official police product.
- Always call **911** for emergencies.

## License

MIT
