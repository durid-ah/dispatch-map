# packages/web

Vite + React + TypeScript frontend for dispatch-map.

## Scripts

```bash
npm install --prefix packages/web
npm run dev --prefix packages/web
npm run build --prefix packages/web
npm run lint --prefix packages/web
```

## Integration with FastAPI

- **Development:** Vite proxies `/items` to `http://127.0.0.1:8000` (see `vite.config.ts`).
- **Production:** `npm run build` writes to `packages/api/static/app`, which FastAPI serves with an SPA fallback for client-side routes.
