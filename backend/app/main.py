from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Notice the 'backend.app...' absolute imports
from backend.app.api.connections import router as connections_router
from backend.app.api.metadata import router as metadata_router
from backend.app.database.session_manager import session_manager
from backend.app.database.pool_manager import pool_manager
from backend.app.api.agent import router as agent_router
from backend.app.api.catalog import router as catalog_router

app = FastAPI(title="Production Database Agent API", version="1.0.0")

# CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registering our routers
app.include_router(connections_router, prefix="/api/v1", tags=["Connections"])
app.include_router(metadata_router, prefix="/api/v1", tags=["Metadata"])
app.include_router(agent_router, prefix="/api/v1", tags=["Agent"])
app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["Catalog"])

@app.on_event("shutdown")
def shutdown_event():
    """Ensure all resources are gracefully released on app termination."""
    session_manager.close_all()
    pool_manager.dispose_all()

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Agent API Layer"}