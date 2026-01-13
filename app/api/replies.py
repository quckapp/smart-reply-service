"""Smart reply API endpoints."""

from fastapi import APIRouter, HTTPException

from app.services.reply_service import reply_service
from app.schemas.reply import (
    ReplyRequest,
    ReplyResponse,
    QuickReplyRequest,
    QuickReplyResponse,
)

router = APIRouter()


@router.post("/suggest", response_model=ReplyResponse)
async def suggest_replies(request: ReplyRequest):
    """Generate smart reply suggestions based on conversation context.

    This endpoint analyzes the conversation context and generates
    AI-powered reply suggestions appropriate for the tone and context.
    """
    if not request.context.messages:
        raise HTTPException(
            status_code=400,
            detail="At least one message is required in the context",
        )

    return await reply_service.generate_replies(request)


@router.post("/quick", response_model=QuickReplyResponse)
async def quick_replies(request: QuickReplyRequest):
    """Get quick reply options for a single message.

    This is a lighter-weight endpoint for getting simple
    quick reply options without full context.
    """
    return await reply_service.get_quick_replies(request)


@router.get("/intents")
async def list_intents():
    """List available reply intents."""
    from app.schemas.reply import ReplyIntent

    return {
        "intents": [intent.value for intent in ReplyIntent],
    }


@router.get("/tones")
async def list_tones():
    """List available reply tones."""
    from app.schemas.reply import ReplyTone

    return {
        "tones": [tone.value for tone in ReplyTone],
    }
