"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter

from app.services.reply_service import reply_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "smart-reply-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check including ML models."""
    status = {
        "status": "ready",
        "service": "smart-reply-service",
        "timestamp": datetime.utcnow().isoformat(),
        "models": {
            "reply_model": "loaded" if reply_service.initialized else "fallback",
        },
    }

    if not reply_service.initialized:
        status["status"] = "degraded"
        status["message"] = "ML models not loaded, using fallback templates"

    return status


@router.get("/health/live")
async def liveness_check():
    """Liveness check."""
    return {
        "status": "alive",
        "service": "smart-reply-service",
        "timestamp": datetime.utcnow().isoformat(),
    }
