"""The workutil application: one FastAPI app serving the API and the UI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import HOST, PORT, Settings, load_settings
from app.core.db import create_db_engine, create_session_factory, migrate_to_head
from app.modules.registry import ROUTERS


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.create_directories()

    engine = create_db_engine(settings)
    migrate_to_head(engine)

    app = FastAPI(title="workutil", lifespan=_lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    for router in ROUTERS:
        app.include_router(router, prefix="/api")

    # In production the UI is the frontend build, served by this same process,
    # so the work machine needs Python and nothing else (docs/design.md §3.1).
    # While developing, the Vite dev server plays that part and this is absent.
    if settings.frontend_dist.is_dir():
        ui = StaticFiles(directory=settings.frontend_dist, html=True)
        app.mount("/", ui, name="ui")

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT)
