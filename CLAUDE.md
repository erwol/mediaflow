# mediaflow

Self-hosted media download manager. FastAPI backend + React/Vite frontend, deployed as two Docker services on a Raspberry Pi 5 running OpenMediaVault.

## Quick commands

```bash
make dev          # start hot-reload dev stack
make lint         # ruff + black --check (backend) + tsc + prettier --check (frontend)
make format       # black (backend) + prettier (frontend)
make build        # build Docker images locally
make prod         # start production stack
```

## Project structure

```
backend/app/
  core/config.py      # pydantic-settings, reads env vars
  models/schemas.py   # all Pydantic v2 models (ParseResult, DownloadJob, …)
  services/parser.py  # parse_url(): guessit → ParseResult
  services/downloader.py  # in-memory job dict, httpx streaming downloads
  routers/parse.py    # POST /api/parse
  routers/download.py # POST /api/download, GET /api/jobs, GET /api/jobs/{id}

frontend/src/
  types/index.ts      # mirrors backend schemas exactly
  api/client.ts       # typed fetch wrapper, base = /api
  hooks/useDownloads.ts  # TanStack Query mutations + polling
  components/UrlInput.tsx
  components/UrlCard.tsx
```

## Tech stack

- **Backend**: Python 3.12, FastAPI ≥ 0.115, Pydantic v2, httpx (streaming), guessit
- **Frontend**: React 19, TypeScript strict, Vite 6, Tailwind v4, TanStack Query v5
- **Infra**: nginx (in the frontend container), Docker Compose, GHCR multi-arch images

## Key conventions

- **Pydantic v2**: use `model_config = ConfigDict(...)`, not `class Config`
- **Tailwind v4**: `@import "tailwindcss"` in CSS — no `@tailwind` directives
- **TanStack Query v5**: `useMutation` / `useQuery` only — no Redux/Zustand
- **No auth**: LAN-only tool, intentionally unauthenticated
- **No database**: jobs live in an in-memory dict; they reset on restart
- **Downloads**: httpx async streaming into `Path.open("wb")`, 1 MB chunks
- **Jellyfin paths**: movies → `MOVIES_DIR/Title (Year).mkv`; episodes → `TVSHOWS_DIR/Show/Season 02/Show S02E04.mkv`

## Linting & formatting

| Tool | Scope | Config |
|------|-------|--------|
| ruff | Python lint | `pyproject.toml` `[tool.ruff]` |
| black | Python format | `pyproject.toml` `[tool.black]` |
| tsc | TS type-check | `frontend/tsconfig.json` |
| prettier | TS/TSX format | `frontend/.prettierrc` |

CI (`build.yml`) runs all four checks in a `lint` job before building images.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOVIES_DIR` | `/home/pi/movies` | Root dir for movie downloads |
| `TVSHOWS_DIR` | `/home/pi/tvshows` | Root dir for TV show downloads |
| `DOWNLOAD_TIMEOUT` | `3600` | Max seconds per download |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:80"]` | Allowed origins |

## Docker images

Built for `linux/amd64` + `linux/arm64` via QEMU on every push to `main`:
- `ghcr.io/erwol/mediaflow-backend:latest`
- `ghcr.io/erwol/mediaflow-frontend:latest`
