from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import STATIC_DIR
from routers import events_router, items_router, spa_router

app = FastAPI(title="Dispatch Map API")

# Mount static asset directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Register API routers (API routes first, SPA catch-all last)
app.include_router(events_router)
app.include_router(items_router)
app.include_router(spa_router)
