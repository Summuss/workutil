"""The workutil application: one FastAPI app serving the API and the UI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import PurePosixPath

from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from starlette.types import Scope

from app.core.config import HOST, PORT, Settings, load_settings
from app.core.db import create_db_engine, create_session_factory, migrate_to_head
from app.core.platform import Platform, UnsupportedPlatformError, get_default_platform
from app.modules.registry import ROUTERS


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.engine.dispose()


class SinglePageApp(StaticFiles):
    """The frontend build, with the frontend's own router left in charge of URLs.

    Why this exists rather than a plain `StaticFiles`: see design.md §3.1. In
    short, a path with no file behind it may still be the frontend's, and has
    to come back as the app; anything that plainly wants a *file* keeps its
    404.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        if not _is_a_frontend_route(path):
            return await super().get_response(path, scope)

        # A miss arrives two different ways: `StaticFiles` raises, unless the
        # build happens to carry a `404.html`, in which case it hands back a
        # 404 response instead. Vite emits no such file today — but if one ever
        # appears, reloading `/evidence` must not quietly start failing again.
        try:
            found = await super().get_response(path, scope)
        except HTTPException as missing:
            if missing.status_code != 404:
                raise
        else:
            if found.status_code != 404:
                return found

        return await super().get_response("index.html", scope)


def _is_a_frontend_route(path: str) -> bool:
    """Would react-router recognise this path, or is something asking for a file?

    A stale `<script src>` handed `index.html` fails as a MIME-type error deep
    in the console instead of an obvious 404, and a mistyped fetch URL must not
    come back looking like a page — so extensions and `/api` are not ours.
    """
    first, _, _ = path.partition("/")
    return first != "api" and "." not in PurePosixPath(path).name


def create_app(
    settings: Settings | None = None,
    platform: Platform | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    settings.create_directories()

    engine = create_db_engine(settings)
    migrate_to_head(engine)

    app = FastAPI(title="workutil", lifespan=_lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.platform = platform or get_default_platform()

    @app.exception_handler(UnsupportedPlatformError)
    async def unsupported_platform_handler(
        request: Request, exc: UnsupportedPlatformError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={"code": exc.code, "detail": str(exc)},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        content: dict[str, str | None]
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code")
            msg = (
                exc.detail.get("message") or exc.detail.get("detail") or str(exc.detail)
            )
            content = {"code": code, "detail": msg}
        else:
            content = {"detail": exc.detail}
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )

    for router in ROUTERS:
        app.include_router(router, prefix="/api")

    # In production the UI is the frontend build, served by this same process,
    # so the work machine needs Python and nothing else (docs/design.md §3.1).
    # While developing, the Vite dev server plays that part and this is absent.
    if settings.frontend_dist.is_dir():
        ui = SinglePageApp(directory=settings.frontend_dist, html=True)
        app.mount("/", ui, name="ui")

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT)
