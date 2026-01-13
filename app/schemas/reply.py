"""Reply schema definitions."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ReplyTone(str, Enum):
    """Reply tone options."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"


class ReplyIntent(str, Enum):
    """Reply intent categories."""

    ACKNOWLEDGE = "acknowledge"
    AGREE = "agree"
    DISAGREE = "disagree"
    QUESTION = "question"
    ANSWER = "answer"
    THANKS = "thanks"
    GREETING = "greeting"
    FAREWELL = "farewell"
    SUGGESTION = "suggestion"
    GENERAL = "general"


class Message(BaseModel):
    """A message in a conversation."""

    id: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=4000)
    sender_id: str
    sender_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_current_user: bool = False


class ConversationContext(BaseModel):
    """Conversation context for reply generation."""

    messages: List[Message] = Field(
        ..., min_length=1, max_length=20, description="Recent messages in the conversation"
    )
    channel_name: Optional[str] = None
    channel_type: Optional[str] = None  # "dm", "channel", "thread"
    workspace_id: Optional[str] = None


class ReplyRequest(BaseModel):
    """Request for smart reply suggestions."""

    context: ConversationContext
    current_user_id: str
    current_user_name: Optional[str] = None
    tone: ReplyTone = ReplyTone.PROFESSIONAL
    num_suggestions: int = Field(default=3, ge=1, le=5)
    max_length: int = Field(default=100, ge=10, le=500)
    include_quick_replies: bool = True


class ReplySuggestion(BaseModel):
    """A single reply suggestion."""

    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    intent: ReplyIntent
    tone: ReplyTone
    is_quick_reply: bool = False


class ReplyResponse(BaseModel):
    """Response with reply suggestions."""

    suggestions: List[ReplySuggestion]
    context_summary: Optional[str] = None
    processing_time_ms: float
    model_version: str = "1.0.0"


class QuickReplyRequest(BaseModel):
    """Request for quick reply options."""

    last_message: str = Field(..., min_length=1, max_length=4000)
    sender_name: Optional[str] = None


class QuickReplyResponse(BaseModel):
    """Quick reply options response."""

    replies: List[str]
    intent: ReplyIntent
