from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.errors import register_exception_handlers
from app.legacy import brew_logs as legacy_brew_logs
from app.routers import equipment_sets, pages
from app.templating import PROJECT_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Coffee Log Web", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")

register_exception_handlers(app)

app.include_router(equipment_sets.router)
app.include_router(pages.router)
# Legacy BrewLog / Evaluation domain. Removed in the last migration step (PR9).
app.include_router(legacy_brew_logs.router)
