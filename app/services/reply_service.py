"""Smart reply generation service."""

import time
import re
from typing import List, Optional
import structlog

from app.core.config import settings
from app.schemas.reply import (
    ReplyRequest,
    ReplySuggestion,
    ReplyResponse,
    ReplyTone,
    ReplyIntent,
    QuickReplyRequest,
    QuickReplyResponse,
    Message,
)

logger = structlog.get_logger()


class SmartReplyService:
    """Service for generating smart reply suggestions."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.embedding_model = None
        self.initialized = False

        # Quick reply templates by intent
        self.quick_reply_templates = {
            ReplyIntent.ACKNOWLEDGE: [
                "Got it, thanks!",
                "Understood",
                "Sounds good",
                "Noted, thank you",
            ],
            ReplyIntent.AGREE: [
                "I agree",
                "That makes sense",
                "Absolutely",
                "Good point",
            ],
            ReplyIntent.DISAGREE: [
                "I have a different view",
                "Let me share another perspective",
                "I'm not sure about that",
            ],
            ReplyIntent.THANKS: [
                "Thank you!",
                "Thanks for your help",
                "Much appreciated",
                "Thanks!",
            ],
            ReplyIntent.GREETING: [
                "Hi there!",
                "Hello!",
                "Hey!",
                "Good to hear from you",
            ],
            ReplyIntent.FAREWELL: [
                "Talk soon!",
                "Have a great day!",
                "Take care",
                "Bye for now",
            ],
            ReplyIntent.QUESTION: [
                "Could you clarify?",
                "What do you think?",
                "Any thoughts on this?",
            ],
        }

        # Intent detection patterns
        self.intent_patterns = {
            ReplyIntent.GREETING: r"\b(hi|hello|hey|good morning|good afternoon)\b",
            ReplyIntent.FAREWELL: r"\b(bye|goodbye|see you|talk later|take care)\b",
            ReplyIntent.THANKS: r"\b(thank|thanks|appreciate|grateful)\b",
            ReplyIntent.QUESTION: r"\?$|\b(what|how|why|when|where|who|could you|can you)\b",
        }

    async def initialize(self) -> None:
        """Initialize ML models."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info("Loading smart reply models...")

            self.tokenizer = AutoTokenizer.from_pretrained(settings.REPLY_MODEL)
            self.model = AutoModelForCausalLM.from_pretrained(settings.REPLY_MODEL)

            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.initialized = True
            logger.info("Smart reply models loaded successfully")

        except Exception as e:
            logger.warning(f"Failed to load ML models, using fallback: {e}")
            self.initialized = False

    async def generate_replies(self, request: ReplyRequest) -> ReplyResponse:
        """Generate smart reply suggestions."""
        start_time = time.time()

        # Build context string
        context_str = self._build_context_string(request.context.messages)

        # Detect intent from last message
        last_message = request.context.messages[-1]
        detected_intent = self._detect_intent(last_message.content)

        suggestions = []

        # Generate ML-based suggestions if available
        if self.initialized and self.model is not None:
            ml_suggestions = await self._generate_ml_replies(
                context_str,
                request.num_suggestions,
                request.max_length,
                request.tone,
            )
            suggestions.extend(ml_suggestions)

        # Add quick replies if requested
        if request.include_quick_replies:
            quick_replies = self._get_quick_replies(detected_intent, request.tone)
            suggestions.extend(quick_replies)

        # If no ML suggestions, use template-based fallback
        if not suggestions:
            suggestions = self._generate_fallback_replies(
                last_message.content,
                detected_intent,
                request.tone,
                request.num_suggestions,
            )

        # Sort by confidence and limit
        suggestions = sorted(suggestions, key=lambda x: x.confidence, reverse=True)
        suggestions = suggestions[: request.num_suggestions]

        processing_time = (time.time() - start_time) * 1000

        return ReplyResponse(
            suggestions=suggestions,
            context_summary=self._summarize_context(request.context.messages),
            processing_time_ms=processing_time,
        )

    def _build_context_string(self, messages: List[Message]) -> str:
        """Build a context string from messages."""
        context_parts = []
        for msg in messages[-settings.MAX_CONTEXT_MESSAGES :]:
            sender = msg.sender_name or msg.sender_id
            context_parts.append(f"{sender}: {msg.content}")
        return "\n".join(context_parts)

    def _detect_intent(self, text: str) -> ReplyIntent:
        """Detect the intent of a message."""
        text_lower = text.lower()

        for intent, pattern in self.intent_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return intent

        return ReplyIntent.GENERAL

    async def _generate_ml_replies(
        self,
        context: str,
        num_suggestions: int,
        max_length: int,
        tone: ReplyTone,
    ) -> List[ReplySuggestion]:
        """Generate replies using ML model."""
        suggestions = []

        try:
            # Encode context
            inputs = self.tokenizer.encode(
                context + self.tokenizer.eos_token,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )

            # Generate multiple responses
            outputs = self.model.generate(
                inputs,
                max_length=inputs.shape[1] + max_length,
                num_return_sequences=num_suggestions,
                do_sample=True,
                top_p=0.92,
                top_k=50,
                temperature=0.7,
                pad_token_id=self.tokenizer.pad_token_id,
                no_repeat_ngram_size=3,
            )

            for i, output in enumerate(outputs):
                # Decode and extract just the generated part
                full_text = self.tokenizer.decode(output, skip_special_tokens=True)
                # Remove the context part
                reply_text = full_text[len(context) :].strip()

                if reply_text and len(reply_text) > 3:
                    # Clean up the reply
                    reply_text = self._clean_reply(reply_text)

                    suggestions.append(
                        ReplySuggestion(
                            text=reply_text,
                            confidence=0.7 - (i * 0.1),  # Decreasing confidence
                            intent=self._detect_intent(reply_text),
                            tone=tone,
                            is_quick_reply=False,
                        )
                    )

        except Exception as e:
            logger.error(f"ML reply generation failed: {e}")

        return suggestions

    def _clean_reply(self, text: str) -> str:
        """Clean up generated reply text."""
        # Remove any remaining special tokens
        text = re.sub(r"<\|.*?\|>", "", text)
        # Remove extra whitespace
        text = " ".join(text.split())
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        # Ensure proper ending
        if text and text[-1] not in ".!?":
            text += "."
        return text

    def _get_quick_replies(
        self, intent: ReplyIntent, tone: ReplyTone
    ) -> List[ReplySuggestion]:
        """Get quick reply suggestions based on intent."""
        templates = self.quick_reply_templates.get(intent, [])

        suggestions = []
        for i, template in enumerate(templates[:2]):  # Max 2 quick replies
            # Adjust template based on tone
            adjusted = self._adjust_for_tone(template, tone)
            suggestions.append(
                ReplySuggestion(
                    text=adjusted,
                    confidence=0.8 - (i * 0.1),
                    intent=intent,
                    tone=tone,
                    is_quick_reply=True,
                )
            )

        return suggestions

    def _adjust_for_tone(self, text: str, tone: ReplyTone) -> str:
        """Adjust reply text based on tone."""
        if tone == ReplyTone.FORMAL:
            # Make more formal
            replacements = {
                "Thanks!": "Thank you.",
                "Got it": "Understood",
                "Sounds good": "That works well",
                "Hi there!": "Hello,",
                "Hey!": "Hello,",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)

        elif tone == ReplyTone.CASUAL:
            # Make more casual
            replacements = {
                "Thank you.": "Thanks!",
                "Understood": "Got it!",
                "Hello,": "Hey!",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)

        return text

    def _generate_fallback_replies(
        self,
        last_message: str,
        intent: ReplyIntent,
        tone: ReplyTone,
        num_suggestions: int,
    ) -> List[ReplySuggestion]:
        """Generate fallback replies when ML model is unavailable."""
        suggestions = []

        # Get templates for detected intent
        templates = self.quick_reply_templates.get(
            intent, self.quick_reply_templates[ReplyIntent.ACKNOWLEDGE]
        )

        for i, template in enumerate(templates[:num_suggestions]):
            adjusted = self._adjust_for_tone(template, tone)
            suggestions.append(
                ReplySuggestion(
                    text=adjusted,
                    confidence=0.6 - (i * 0.1),
                    intent=intent,
                    tone=tone,
                    is_quick_reply=True,
                )
            )

        return suggestions

    def _summarize_context(self, messages: List[Message]) -> str:
        """Create a brief summary of the conversation context."""
        if not messages:
            return "No context available"

        num_messages = len(messages)
        unique_senders = len(set(m.sender_id for m in messages))

        return f"Conversation with {unique_senders} participant(s), {num_messages} recent message(s)"

    async def get_quick_replies(self, request: QuickReplyRequest) -> QuickReplyResponse:
        """Get quick reply options for a message."""
        intent = self._detect_intent(request.last_message)
        templates = self.quick_reply_templates.get(
            intent, self.quick_reply_templates[ReplyIntent.ACKNOWLEDGE]
        )

        return QuickReplyResponse(
            replies=templates[:4],
            intent=intent,
        )


# Global service instance
reply_service = SmartReplyService()
