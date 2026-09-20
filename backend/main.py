"""FastAPI application entry point.

Wires together all routers and serves the compiled React frontend as a
static Single-Page Application at the root URL.  The frontend ``dist/``
folder is built separately via ``npm run build`` inside ``frontend/``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.a2a.router import a2a_router, well_known_router
from backend.routes import agent, artifacts

app = FastAPI(title="Forge Agent API", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(artifacts.router)
app.include_router(well_known_router, tags=["a2a"])
app.include_router(a2a_router, prefix="/a2a", tags=["a2a"])


@app.get("/health", tags=["infra"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ── Serve compiled React SPA ───────────────────────────────────────────────
# Mount AFTER API routes so /api/* is never intercepted by the static handler.
# Falls back gracefully if dist/ hasn't been built yet (dev-only uvicorn run).
_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _dist.exists():
    # Serve all static assets (JS, CSS, images) from dist/assets
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    # SPA catch-all: serve index.html for every non-API route so that
    # client-side routing works correctly.
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        """Serve the React SPA for any path not matched by an API route."""
        index = _dist / "index.html"
        return FileResponse(str(index))
