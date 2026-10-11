from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from atlas.persistence.db import init_db
from backend.api.health import router as health_router
from backend.api.datasets import router as datasets_router
from backend.api.analyses import router as analyses_router
from backend.api.memories import router as memories_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    init_db()
    yield

app = FastAPI(
    title="ATLAS - Agentic Tabular Intelligence",
    description="Universal tabular intelligence engine with structured planning, deterministic execution, and cross-session domain memory.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(datasets_router)
app.include_router(analyses_router)
app.include_router(memories_router)

PUBLIC_DIR = Path(__file__).parent.parent / "public"

@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(PUBLIC_DIR / "index.html")

@app.get("/demo_retail_orders.csv", include_in_schema=False)
def serve_demo_csv():
    return FileResponse(PUBLIC_DIR / "demo_retail_orders.csv")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
