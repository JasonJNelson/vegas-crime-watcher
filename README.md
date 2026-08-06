# Vegas Crime Watcher

[![CI](https://github.com/JasonJNelson/vegas-crime-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/JasonJNelson/vegas-crime-watcher/actions/workflows/ci.yml)

Interactive Las Vegas crime map and feed.

- **Local / Railway / Docker:** long-running pure-Python server (`app.py`)
- **Vercel:** static UI + serverless Python APIs

## Run locally

```bash
python app.py
# → http://127.0.0.1:8080  (localhost only by default)
```

## Deploy on Vercel (public URL)

1. Open [vercel.com/new](https://vercel.com/new)
2. Import **JasonJNelson/vegas-crime-watcher**
3. Deploy (defaults are fine)
4. Open the URL Vercel prints (e.g. `https://vegas-crime-watcher.vercel.app`)

CLI:

```bash
npm i -g vercel
vercel login
vercel --prod
```

| Path | Runtime |
|------|---------|
| `/` | Static `public/index.html` |
| `/api/crimes` | Serverless (seed + on-demand ArcGIS) |
| `/api/health` | Serverless |
| `/api/simulate` | Serverless |

## Deploy on Railway

Use `Dockerfile` / `railway.toml`. Background ArcGIS poller runs there.

## Security

Local default bind is `127.0.0.1`. Public bind when `PORT` is set (Railway) or `ALLOW_PUBLIC=1`.

## License

MIT
