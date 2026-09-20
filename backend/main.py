from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.a2a.router import a2a_router, well_known_router
from backend.routes import agent

app = FastAPI(title="Forge Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(well_known_router, tags=["a2a"])
app.include_router(a2a_router, prefix="/a2a", tags=["a2a"])

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
