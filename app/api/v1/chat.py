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


def _extract_answer_from_cache(cached: object) -> str:
    """
    Normalize cache payload across endpoints.
    Cache entries may be plain strings (legacy) or dicts like {"answer": "..."}.
    """
    if isinstance(cached, dict):
        value = cached.get("answer", "")
        return value if isinstance(value, str) else str(value)
    if isinstance(cached, str):
        return cached
    return str(cached) if cached is not None else ""


# ================= NEW REQUEST/RESPONSE MODELS =================
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    answer: str
    intent: str
    show_lead_form: bool = False
    follow_up: Optional[str] = None
    enquiry_message: Optional[str] = None


# ================= NEW ENDPOINT WITH INTENT DETECTION =================
@router.post("/message", response_model=MessageResponse)
async def message_endpoint(req: MessageRequest) -> MessageResponse:
    """
    POST /v1/message — Intent detection + RAG chat
    Handles intent detection and returns structured response
    """
    try:
        logger.info(f"📨 /v1/message received: {req.message[:80]}")
        
        # Check if intent engine can handle it
        intent_response = get_intent_response(req.message)
        
        if intent_response:
            # Intent matched - return predefined response
            logger.info(f"🎯 Intent matched: {intent_response.get('intent')}")
            return MessageResponse(
                answer=intent_response["answer"],
                intent=intent_response["intent"],
                show_lead_form=intent_response["show_lead_form"],
                follow_up=intent_response.get("follow_up"),
                enquiry_message=intent_response.get("enquiry_message"),
            )
        
        logger.info(f"🔄 No intent match, routing to RAG...")
        
        # Intent type is "general" - use RAG
        cache_key = get_cache_key(req.message)
        if cache_key in _cache:
            logger.info(f"⚡ Cache hit: {req.message[:50]}")
            answer = _extract_answer_from_cache(_cache[cache_key])
            return MessageResponse(
                answer=answer,
                intent="general",
                show_lead_form=False,
                follow_up=None,
                enquiry_message=None,
            )

        # Run with 12s timeout
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message),
            timeout=12.0
        )

        # Extract answer from result dict
        answer = result.get("answer")
        if not isinstance(answer, str):
            answer = str(answer) if answer is not None else ""
        has_answer = result.get("has_answer", False)
        
        logger.info(f"✅ RAG result: has_answer={has_answer}, answer starts with: {answer[:100] if answer else 'None'}")

        # Cache only meaningful answers, not fallback error text.
        if has_answer:
            if len(_cache) >= 50:
                del _cache[next(iter(_cache))]
            _cache[cache_key] = {"answer": answer}

        return MessageResponse(
            answer=answer,
            intent="general",
            show_lead_form=False,
            follow_up=None,
            enquiry_message=None,  # No enquiry message for normal RAG conversation
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
            answer = _extract_answer_from_cache(_cache[cache_key])
            return ChatResponse(answer=answer)

        # ✅ Run with 8s timeout (prevents hanging)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message),
            timeout=12.0
        )

        # Extract answer from result dict
        answer = result.get("answer", "")
        has_answer = bool(result.get("has_answer", False))
        if not isinstance(answer, str):
            answer = str(answer) if answer is not None else ""

        # ✅ Store in cache only for successful answers.
        if has_answer:
            if len(_cache) >= 50:
                del _cache[next(iter(_cache))]
            _cache[cache_key] = {"answer": answer}

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
