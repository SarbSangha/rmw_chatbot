# app/api/v1/chat.py
import asyncio
import hashlib
import logging

from fastapi import APIRouter
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import run_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["chat"])

# ✅ Simple in-memory cache (max 50 entries)
_cache: dict = {}


def get_cache_key(message: str) -> str:
    return hashlib.md5(message.strip().lower().encode()).hexdigest()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """
    POST /v1/chat — with caching + 8s timeout
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
