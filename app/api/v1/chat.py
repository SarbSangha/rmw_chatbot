# app/api/v1/chat.py
import asyncio
import hashlib
import logging
import re
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import (
    run_chat,
    build_parallel_context,
    needs_external_web_fallback,
    extract_founded_year_answer,
)
from app.rag.graph import RAGState, answer_node_streaming
from app.utils.intent_engine import get_intent_response
from app.utils.intent_engine import is_external_query
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["chat"])

# ✅ Simple in-memory cache (max 50 entries)
_cache: dict = {}

# Website URL for web search
WEBSITE_URL = "https://ritzmediaworld.com"
CHAT_TIMEOUT_SECONDS = 12.0


def get_cache_key(message: str, developer_context: str = "") -> str:
    raw = f"{message.strip().lower()}|{(developer_context or '').strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


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
    developer_context: Optional[str] = None


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
        cache_key = get_cache_key(req.message, req.developer_context or "")
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
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message, req.developer_context or ""),
            timeout=CHAT_TIMEOUT_SECONDS
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
            enquiry_message=None,
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
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_chat, req.message),
            timeout=CHAT_TIMEOUT_SECONDS
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


# ================= STREAMING ENDPOINT WITH WEB SEARCH =================

def _split_word_safe_chunks(buffer: str) -> tuple[list[str], str]:
    if not buffer:
        return [], ""
    if not re.search(r"\s", buffer):
        return [], buffer

    last_space_index = max(buffer.rfind(" "), buffer.rfind("\n"), buffer.rfind("\t"))
    if last_space_index <= 0:
        return [], buffer

    ready_text = buffer[: last_space_index + 1]
    remaining = buffer[last_space_index + 1 :]
    parts = [part for part in re.findall(r"\S+\s*", ready_text) if part]
    return parts, remaining


def _iter_word_chunks(text: str) -> list[str]:
    return [part for part in re.findall(r"\S+\s*", text or "") if part]


async def stream_rag_response(question: str, developer_context: str = ""):
    """
    Generator function that yields streaming response chunks.
    Includes web search from ritzmediaworld.com
    """
    try:
        loop = asyncio.get_running_loop()
        context_bundle = await loop.run_in_executor(
            None,
            build_parallel_context,
            question,
            WEBSITE_URL,
            True,
            developer_context or "",
        )
        
        # Build initial state with web context
        state: RAGState = {
            "question": question,
            "docs": context_bundle.get("docs", []),
            "answer": "",
            "web_context": context_bundle.get("web_context", ""),
            "developer_context": context_bundle.get("developer_context", ""),
            "external_context": "",
        }
        
        logger.info(
            "🚀 Starting RAG streaming for: %s | docs=%d web_chars=%d dev_chars=%d",
            question[:30],
            len(state.get("docs", [])),
            len(state.get("web_context", "")),
            len(state.get("developer_context", "")),
        )

        # Deterministic fast path for foundational year queries.
        founded_year_answer = extract_founded_year_answer(
            question=question,
            docs=state.get("docs", []),
            web_context=state.get("web_context", ""),
        )
        if founded_year_answer:
            for word in _iter_word_chunks(founded_year_answer):
                yield f"data: {json.dumps({'chunk': word})}\n\n"
            yield f"data: {json.dumps({'final': True, 'answer': founded_year_answer})}\n\n"
            return
        
        # For clearly external queries, build merged two-part answer via service
        # and stream that directly word-by-word.
        if is_external_query(question):
            loop = asyncio.get_running_loop()
            merged_result = await loop.run_in_executor(
                None,
                run_chat,
                question,
                developer_context or "",
            )
            merged_answer = (merged_result.get("answer") or "").strip()
            for word in _iter_word_chunks(merged_answer):
                yield f"data: {json.dumps({'chunk': word})}\n\n"
            yield f"data: {json.dumps({'final': True, 'answer': merged_answer})}\n\n"
            return

        # Non-external query: stream directly from generator.
        defer_chunks = False

        # Stream directly from the answer generator so custom stream fields
        # (is_chunk/final_answer) are preserved.
        pending_buffer = ""
        assembled_answer = ""
        final_sent = False
        async for payload in answer_node_streaming(state):
            answer_chunk = payload.get("answer", "")
            is_chunk = bool(payload.get("is_chunk", False))
            final_answer = payload.get("final_answer", "")

            if final_answer and not is_chunk:
                if pending_buffer:
                    if not defer_chunks:
                        yield f"data: {json.dumps({'chunk': pending_buffer})}\n\n"
                    assembled_answer += pending_buffer
                    pending_buffer = ""
                if needs_external_web_fallback(final_answer):
                    logger.info("🔁 Low-confidence final detected, running external fallback.")
                    loop = asyncio.get_running_loop()
                    fallback_result = await loop.run_in_executor(
                        None,
                        run_chat,
                        question,
                        developer_context or "",
                    )
                    upgraded = (fallback_result.get("answer") or "").strip()
                    if upgraded:
                        for word in _iter_word_chunks(upgraded):
                            yield f"data: {json.dumps({'chunk': word})}\n\n"
                        yield f"data: {json.dumps({'final': True, 'answer': upgraded})}\n\n"
                        final_sent = True
                        continue
                logger.info("✅ Sending final answer (%d chars)", len(final_answer))
                yield f"data: {json.dumps({'final': True, 'answer': final_answer})}\n\n"
                final_sent = True
                continue

            if answer_chunk and is_chunk:
                pending_buffer += answer_chunk
                word_chunks, pending_buffer = _split_word_safe_chunks(pending_buffer)
                for word_chunk in word_chunks:
                    assembled_answer += word_chunk
                    if not defer_chunks:
                        yield f"data: {json.dumps({'chunk': word_chunk})}\n\n"

        if not final_sent:
            if pending_buffer:
                assembled_answer += pending_buffer
                if not defer_chunks:
                    yield f"data: {json.dumps({'chunk': pending_buffer})}\n\n"
            final_text = assembled_answer.strip()
            if final_text:
                logger.info("✅ Sending synthesized final answer (%d chars)", len(final_text))
                yield f"data: {json.dumps({'final': True, 'answer': final_text})}\n\n"
            else:
                fallback = "Something went wrong. Please try again."
                yield f"data: {json.dumps({'final': True, 'answer': fallback})}\n\n"
                    
    except Exception as e:
        logger.error(f"❌ Streaming error: {str(e)}")
        yield f"data: {json.dumps({'error': 'Something went wrong. Please try again.'})}\n\n"


@router.post("/message/stream")
async def message_stream_endpoint(req: MessageRequest):
    """
    POST /v1/message/stream — Streaming chat endpoint
    Returns SSE (Server-Sent Events) stream for real-time response
    Includes web search from ritzmediaworld.com
    """
    try:
        logger.info(f"📨 /v1/message/stream received: {req.message[:80]}")
        
        # Check intent engine first (for quick responses)
        intent_response = get_intent_response(req.message)
        
        if intent_response:
            # Return instant response for intents
            logger.info(f"🎯 Intent matched (streaming): {intent_response.get('intent')}")
            answer = intent_response["answer"]
            # Stream response word-by-word for consistency.
            async def intent_stream():
                for word in _iter_word_chunks(answer):
                    yield f"data: {json.dumps({'chunk': word})}\n\n"
                yield f"data: {json.dumps({'final': True, 'answer': answer})}\n\n"
            
            return StreamingResponse(
                intent_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # No intent match - use RAG streaming with web search
        logger.info(f"🔄 No intent match, routing to RAG streaming with web search...")
        
        return StreamingResponse(
            stream_rag_response(req.message, req.developer_context or ""),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Stream endpoint error: {str(e)}")
        async def error_stream():
            yield f"data: {json.dumps({'error': 'Something went wrong. Please try again.'})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )
