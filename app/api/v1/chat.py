# app/api/v1/chat.py
import asyncio
import hashlib
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import run_chat
from app.utils.intent_engine import get_intent_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["chat"])

# ✅ Simple in-memory cache (max 50 entries)
_cache: dict = {}


def get_cache_key(message: str) -> str:
    return hashlib.md5(message.strip().lower().encode()).hexdigest()


# ================= NEW REQUEST/RESPONSE MODELS =================
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    answer: str
    intent: str
    show_lead_form: bool = False
    follow_up: Optional[str] = None
    sources: Optional[list] = None


# ================= NEW ENDPOINT WITH INTENT DETECTION =================
@router.post("/message", response_model=MessageResponse)
async def message_endpoint(req: MessageRequest) -> MessageResponse:
    """
    POST /v1/message — Intent detection + RAG chat
    Handles intent detection and returns structured response
    """
    try:
        # Check if intent engine can handle it
        intent_response = get_intent_response(req.message)
        
        if intent_response:
            # Intent matched - return predefined response
            return MessageResponse(
                answer=intent_response["answer"],
                intent=intent_response["intent"],
                show_lead_form=intent_response["show_lead_form"],
                follow_up=intent_response.get("follow_up"),
            )
        
        # Intent type is "general" - use RAG
        cache_key = get_cache_key(req.message)
        if cache_key in _cache:
            logger.info(f"⚡ Cache hit: {req.message[:50]}")
            return MessageResponse(
                answer=_cache[cache_key],
                intent="general",
                show_lead_form=False,
                follow_up=None,  # No follow-up for normal conversation
            )

        # Run with 12s timeout
        loop = asyncio.get_event_loop()
        answer = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message),
            timeout=12.0
        )

        # Store in cache
        if len(_cache) >= 50:
            del _cache[next(iter(_cache))]
        _cache[cache_key] = answer

        return MessageResponse(
            answer=answer,
            intent="general",
            show_lead_form=False,
            follow_up=None,  # No follow-up for normal conversation
        )

    except asyncio.TimeoutError:
        logger.warning(f"⏳ Timeout: {req.message[:50]}")
        return MessageResponse(
            answer=(
                "⏳ Taking longer than usual. Try asking about a specific service like 'Digital Marketing' for an instant answer, or contact us directly:\n"
                "📞 +91-7290002168"
            ),
            intent="error",
            show_lead_form=False,
        )
    except Exception as e:
        logger.error(f"❌ Endpoint error: {str(e)}")
        return MessageResponse(
            answer=(
                "⚠️ Something went wrong. Please try again or contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            ),
            intent="error",
            show_lead_form=False,
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """
    POST /v1/chat — Legacy endpoint (RAG only, no intent detection)
    """
    try:
        cache_key = get_cache_key(req.message)
        if cache_key in _cache:
            logger.info(f"⚡ Cache hit: {req.message[:50]}")
            return ChatResponse(answer=_cache[cache_key])

        # ✅ Run with 8s timeout (prevents hanging)
        loop = asyncio.get_event_loop()
        answer = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message),
            timeout=12.0
        )

        # ✅ Store in cache (evict oldest if full)
        if len(_cache) >= 50:
            del _cache[next(iter(_cache))]
        _cache[cache_key] = answer

        return ChatResponse(answer=answer)

    except asyncio.TimeoutError:
        logger.warning(f"⏳ Timeout: {req.message[:50]}")
        return ChatResponse(
            answer=(
                "Taking a moment to think! For quick answers, "
                "try asking about 'Digital Marketing' or 'Web Development'.\n"
                "Or reach us directly:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )
        )
    except Exception as e:
        logger.error(f"❌ Endpoint error: {str(e)}")
        return ChatResponse(
            answer=(
                "Something went wrong. Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )
        )
