"""FastAPI application entry point for LiveChat Summarization App."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.routers import webhooks, actions
from app.models.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print(f"Starting LiveChat Summarization App v{__version__}")
    print(f"Environment: {'Development' if settings.debug else 'Production'}")
    yield
    # Shutdown
    print("Shutting down LiveChat Summarization App")


app = FastAPI(
    title="LiveChat Summarization App",
    description="AI-powered chat summarization for LiveChat with CRM integration",
    version=__version__,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(actions.router, prefix="/api", tags=["Actions"])


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow(),
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

