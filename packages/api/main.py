from collections.abc import AsyncIterable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_DIR = STATIC_DIR / "app"

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Item(BaseModel):
    name: str
    description: str | None


items = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box", description="A box that summons a Meeseeks."),
]


@app.get("/items/stream", response_class=EventSourceResponse)
async def sse_items() -> AsyncIterable[Item]:
    for item in items:
        yield item


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


# Catch-all for the React app: /{full_path:path} matches any remaining GET path
# (e.g. /, /assets/..., /map/demo). API routes above take precedence. Look for a
# real file under packages/api/static/app first; otherwise return index.html so
# client-side routes work. Traversal outside APP_DIR is rejected.
@app.get("/{full_path:path}")
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
