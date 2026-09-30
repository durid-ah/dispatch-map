# dispatch-map

Monorepo with a FastAPI backend (`packages/api`), React frontend (`packages/web`), dispatch consumer, shared DB models, and migrations.

## Frontend + API

The React app lives in `packages/web` (Vite). In production, build output goes to `packages/api/static/app` and FastAPI serves it from the same origin.

### Development (two terminals)

```bash
# Terminal 1 — API
uv run fastapi dev packages/api/main.py

# Terminal 2 — React (proxies /items to FastAPI)
npm install --prefix packages/web
npm run dev --prefix packages/web
```

Open the Vite URL (usually `http://127.0.0.1:5173`). API calls to `/items` are proxied to FastAPI on port 8000.

### Production (build, then serve)

```bash
npm run build --prefix packages/web
uv run fastapi run packages/api/main.py
```

Then open `http://127.0.0.1:8000`. The React app is served at `/`; API routes such as `/items/1` and `/items/stream` remain available.

## Local development DB

These are notes for setting up a db for local development. For prod obviously replace the password with a more secure password and config.

`postgresql://dispatch:dispatch@localhost:5432/dispatch_map`

```bash
docker build -t dispatch-map-postgres docker/postgres

docker run -d \
  --name dispatch-map-db \
  -p 5432:5432 \
  -v dispatch_map_pgdata:/var/lib/postgresql/data \
  dispatch-map-postgres
```
