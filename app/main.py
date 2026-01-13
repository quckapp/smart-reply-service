"""
QuikApp Smart Reply Service

Provides AI-powered reply suggestions based on conversation context.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.services.reply_service import reply_service
from app.api import health, replies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup - initialize ML models
    await reply_service.initialize()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="QuikApp Smart Reply Service",
    description="AI-powered reply suggestions API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    replies.router,
    prefix="/api/v1/replies",
    tags=["Smart Replies"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "smart-reply-service",
        "version": "1.0.0",
        "status": "running",
    }
