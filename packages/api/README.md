# packages/api

FastAPI application. Serves JSON/SSE API routes and the React production build from `static/app`.

## Run

```bash
# Development
uv run fastapi dev packages/api/main.py

# Production (build the frontend first)
npm run build --prefix packages/web
uv run fastapi run packages/api/main.py
```

## Static files

- `static/stream.html` — legacy SSE demo page at `/static/stream.html`
- `static/app/` — generated Vite build output (gitignored); served at `/` with SPA fallback
