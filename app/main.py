from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.errors import register_exception_handlers
from app.routers import equipment_sets, experiments, pages, trials
from app.templating import PROJECT_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Coffee Log Web", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")

register_exception_handlers(app)

app.include_router(equipment_sets.router)
app.include_router(experiments.router)
app.include_router(trials.router)
app.include_router(pages.router)
