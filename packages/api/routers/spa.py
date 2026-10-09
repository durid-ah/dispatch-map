from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import APP_DIR

router = APIRouter(tags=["spa"])


@router.get("/{full_path:path}")
async def serve_spa(full_path: str = ""):
    """Serve the React production build, with SPA fallback for client routes."""
    if full_path:
        candidate = (APP_DIR / full_path).resolve()
        try:
            candidate.relative_to(APP_DIR.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        if candidate.is_file():
            return FileResponse(candidate)

    index = APP_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)

    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run: npm run build --prefix packages/web",
    )
