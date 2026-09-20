"""FastAPI application entry point.

Wires together all routers and serves the compiled React frontend as a
static Single-Page Application at the root URL. The frontend ``dist/``
folder is built separately via ``npm run build`` inside ``frontend/``.

Implements REQ-033:
1. Starts at http://localhost:8000 with /docs (Swagger) and /redoc.
2. API versioned under /api/v1/.
3. Endpoints include: auth, users, conversations, messages, agent (run/stream/cancel),
   artifacts, tools, health.
4. All endpoints return consistent JSON response envelopes.
5. Error responses follow RFC 7807 problem details format.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.a2a.router import a2a_router, well_known_router
from backend.db.session import init_db
from backend.problem_details import (
    http_exception_handler,
    validation_exception_handler,
)
from backend.routes import agent, artifacts, auth, conversations, messages, tools, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Initialize database tables on startup
    try:
        init_db()
    except Exception:  # noqa: BLE001, S110
        pass
    yield


app = FastAPI(
    title="Forge Agent API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Exception handlers for RFC 7807 problem details
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Routers (REQ-033)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(artifacts.router)
app.include_router(tools.router)

# A2A Routers
app.include_router(well_known_router, tags=["a2a"])
app.include_router(a2a_router, prefix="/a2a", tags=["a2a"])


# Health endpoints
@app.get("/health", tags=["infra"])
@app.get("/api/v1/health", tags=["infra"])
def health_check() -> dict[str, Any]:
    return {"data": {"status": "ok"}, "status": "ok"}


# ── Serve compiled React SPA ───────────────────────────────────────────────
# Mount AFTER API routes so /api/* is never intercepted by the static handler.
_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        index = _dist / "index.html"
        return FileResponse(str(index))
