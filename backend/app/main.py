from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.workers.processor import run_tick

log = logging.getLogger("fintaxflow")
EXTENSION_PREFIXES = ("/api/import", "/api/billing-batches", "/api/reconciliations", "/api/automation", "/api/declarations", "/api/declaration-receipts", "/api/files", "/api/simulation-portal")


async def _processor_loop(stop: asyncio.Event) -> None:
    settings = get_settings()
    while not stop.is_set():
        try:
            await asyncio.to_thread(run_tick)
        except Exception:
            log.exception("processor loop error")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.processor_poll_seconds)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    stop = asyncio.Event()
    task = None
    if settings.processor_enabled:
        task = asyncio.create_task(_processor_loop(stop))
    yield
    stop.set()
    if task:
        await task


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="FinTaxFlow", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    application.include_router(api_router, prefix="/api")
    from fastapi.staticfiles import StaticFiles
    from app.core.config import REPO_DIR
    application.mount("/simulation-portal", StaticFiles(directory=REPO_DIR / "frontend" / "portal", html=True), name="simulation-portal")
    # X01 logo reference, exposing only public image assets.
    application.mount("/src/static", StaticFiles(directory=REPO_DIR / "frontend" / "src" / "static"), name="portal-assets")

    @application.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        code = exc.code
        if _request.url.path.startswith(EXTENSION_PREFIXES):
            code = {"COMPANY_FORBIDDEN": "FORBIDDEN", "VALIDATION_ERROR": "INVALID_INPUT", "IDEMPOTENCY_REQUIRED": "INVALID_INPUT"}.get(code, code)
        body = {"code": code, "message": exc.message}
        if exc.field_errors:
            body["field_errors"] = exc.field_errors
        return JSONResponse(status_code=exc.status, content=body)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        field_errors: dict[str, str] = {}
        for item in exc.errors():
            loc = ".".join(str(part) for part in item.get("loc", []) if part != "body")
            field_errors[loc or "request"] = item.get("msg", "参数不正确")
        extension_request = _request.url.path.startswith(EXTENSION_PREFIXES)
        return JSONResponse(
            status_code=422 if extension_request else 400,
            content={
                "code": "VALIDATION_FAILED" if extension_request else "VALIDATION_ERROR",
                "message": "请求参数不正确",
                "field_errors": field_errors,
            },
        )

    return application


app = create_app()
