# mediaflow

A self-hosted media download manager for your local network. Paste one or more direct download URLs (e.g. from a seedbox), review the auto-detected filename and destination path (Jellyfin-compatible folder structure), then trigger downloads that run in the background. A live progress bar tracks each download in the browser.

---

## Dev setup

```bash
docker compose up
```

- Backend API with hot reload: [http://localhost:8000](http://localhost:8000)
- Frontend Vite dev server: [http://localhost:5173](http://localhost:5173)

---

## Production setup (Raspberry Pi / OpenMediaVault)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Access the UI at `http://<pi-ip>:3005`.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MOVIES_DIR` | `/home/pi/movies` | Absolute path where movies are saved |
| `TVSHOWS_DIR` | `/home/pi/tvshows` | Absolute path where TV shows are saved |
| `DOWNLOAD_TIMEOUT` | `3600` | Max seconds for a single download |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:80"]` | Allowed CORS origins |

Set these in a `.env` file in the `backend/` directory or via Docker Compose `environment:`.

---

## Updating on the Pi

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```
