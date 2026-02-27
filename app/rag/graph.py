# app/rag/graph.py
import logging
import re
from functools import lru_cache
from typing import TypedDict, List, AsyncGenerator

from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from app.rag.vectorstore import get_retriever
from app.rag.prompts import STRICT_RAG_PROMPT, WEB_RAG_PROMPT, EXTERNAL_FALLBACK_PROMPT
from app.core.config import settings

logger = logging.getLogger(__name__)


def _extract_text(content: object) -> str:
    """
    Extract text robustly from Gemini/LangChain response content payloads.
    Handles strings, dict blocks, and list-of-blocks without dropping segments.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        text_val = content.get("text")
        return text_val if isinstance(text_val, str) else str(text_val or "")

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
                elif text_val is not None:
                    parts.append(str(text_val))
            elif item is not None:
                parts.append(str(item))
        return "".join(parts)

    return str(content)


def _looks_truncated(text: str) -> bool:
    trimmed = (text or "").strip()
    if not trimmed:
        return False
    if len(trimmed) >= 220:
        return False
    return re.search(r"[.!?][\"')\\]]*\s*$", trimmed) is None


class RAGState(TypedDict):
    question: str
    docs: List[Document]
    answer: str
    web_context: str
    developer_context: str
    external_context: str


@lru_cache(maxsize=1)
def _get_llm() -> ChatGoogleGenerativeAI:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.3,
        max_output_tokens=1200,
        top_p=0.95,
        top_k=40,
        convert_system_message_to_human=True,
        max_retries=0,
        request_timeout=20,
    )


@lru_cache(maxsize=1)
def _get_retriever():
    return get_retriever(k=3)


# ================= NODES =================

def retrieve_node(state: RAGState) -> RAGState:
    if state.get("docs"):
        # Docs already prepared upstream (parallel context pipeline).
        return state
    try:
        retriever = _get_retriever()
        docs = retriever.invoke(state["question"]) or []
        logger.info(f"📚 Retrieved {len(docs)} internal docs for: {state['question'][:50]}")
        return {**state, "docs": list(docs)}
    except Exception as e:
        logger.error(f"❌ Retrieval error: {e}")
        return {**state, "docs": []}


def strict_guard_node(state: RAGState) -> RAGState:
    return state


def answer_node(state: RAGState) -> RAGState:
    if state.get("answer"):
        return state

    try:
        context_parts = [doc.page_content[:1500] for doc in state["docs"][:3]]
        context = "\n\n".join(context_parts)
        
        # Check if we have web context
        web_context = state.get("web_context", "")
        developer_context = state.get("developer_context", "")
        external_context = state.get("external_context", "")
        
        # Use dedicated external fallback prompt when external context exists.
        if external_context:
            logger.info(f"🌍 Using external web context: {len(external_context)} chars")
            messages = EXTERNAL_FALLBACK_PROMPT.format_messages(
                external_context=external_context,
                developer_context=developer_context,
                question=state["question"],
            )
        elif web_context:
            logger.info(f"🌐 Using web context: {len(web_context)} chars")
            messages = WEB_RAG_PROMPT.format_messages(
                context=context,
                web_context=web_context,
                developer_context=developer_context,
                external_context=external_context,
                question=state["question"],
            )
        else:
            messages = STRICT_RAG_PROMPT.format_messages(
                context=context,
                developer_context=developer_context,
                external_context=external_context,
                question=state["question"],
            )

        logger.info(f"🤖 Calling Gemini for: {state['question'][:50]}")
        llm = _get_llm()
        resp = llm.invoke(messages)

        # Parse response
        answer_text = _extract_text(getattr(resp, "content", resp))

        answer_text = answer_text.strip()

        if _looks_truncated(answer_text):
            logger.warning("⚠️ Non-stream answer looks truncated (%d chars): %s", len(answer_text), answer_text)
        
        logger.info(f"🤖 Raw Gemini response: {answer_text[:200]}")

        if not answer_text:
            answer_text = (
                "Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )

        logger.info(f"✅ Answer ready ({len(answer_text)} chars): {answer_text[:100]}")
        return {**state, "answer": answer_text}

    except Exception as e:
        error_str = str(e)

        # ✅ Instant quota fallback
        if any(x in error_str for x in ["429", "RESOURCE_EXHAUSTED", "quota", "Quota"]):
            logger.warning("⚠️ Quota exceeded — instant fallback")
            return {
                **state,
                "answer": (
                    "I'm temporarily at capacity 🙏 Please try again in a minute.\n\n"
                    "Or contact our team directly:\n"
                    "📞 +91-7290002168\n"
                    "📧 info@ritzmediaworld.com"
                )
            }

        logger.error(f"❌ LLM error: {error_str}")
        return {
            **state,
            "answer": (
                "Something went wrong. Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )
        }


# ================= STREAMING NODE =================

async def answer_node_streaming(state: RAGState) -> AsyncGenerator[dict, None]:
    """
    Streaming version of answer_node - yields chunks as they come.
    """
    if state.get("answer"):
        yield {"answer": state["answer"]}
        return

    try:
        context_parts = [doc.page_content[:1500] for doc in state["docs"][:3]]
        context = "\n\n".join(context_parts)
        
        # Check if we have web context
        web_context = state.get("web_context", "")
        developer_context = state.get("developer_context", "")
        external_context = state.get("external_context", "")
        
        # Use dedicated external fallback prompt when external context exists.
        if external_context:
            logger.info(f"🌍 Using external web context (streaming): {len(external_context)} chars")
            messages = EXTERNAL_FALLBACK_PROMPT.format_messages(
                external_context=external_context,
                developer_context=developer_context,
                question=state["question"],
            )
        elif web_context:
            logger.info(f"🌐 Using web context (streaming): {len(web_context)} chars")
            messages = WEB_RAG_PROMPT.format_messages(
                context=context,
                web_context=web_context,
                developer_context=developer_context,
                external_context=external_context,
                question=state["question"],
            )
        else:
            messages = STRICT_RAG_PROMPT.format_messages(
                context=context,
                developer_context=developer_context,
                external_context=external_context,
                question=state["question"],
            )

        logger.info(f"🤖 Calling Gemini (streaming) for: {state['question'][:50]}")
        
        full_answer = ""
        
        # Use astream to get streaming response
        llm = _get_llm()
        async for chunk in llm.astream(messages):
            chunk_text = _extract_text(getattr(chunk, "content", chunk))
            
            if chunk_text:
                full_answer += chunk_text
                yield {"answer": chunk_text, "is_chunk": True}

        full_answer = full_answer.strip()
        
        if not full_answer:
            full_answer = (
                "Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )
            yield {"answer": full_answer, "is_chunk": True}
        elif _looks_truncated(full_answer):
            logger.warning("⚠️ Streaming answer looks truncated (%d chars): %s", len(full_answer), full_answer)

        logger.info(f"✅ Streaming complete ({len(full_answer)} chars)")
        yield {"answer": "", "is_chunk": False, "final_answer": full_answer}

    except Exception as e:
        error_str = str(e)

        # ✅ Instant quota fallback
        if any(x in error_str for x in ["429", "RESOURCE_EXHAUSTED", "quota", "Quota"]):
            logger.warning("⚠️ Quota exceeded — instant fallback")
            fallback = (
                "I'm temporarily at capacity 🙏 Please try again in a minute.\n\n"
                "Or contact our team directly:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )
            yield {"answer": fallback, "is_chunk": False, "final_answer": fallback}
            return

        logger.error(f"❌ LLM streaming error: {error_str}")
        error_answer = (
            "Something went wrong. Please contact us:\n"
            "📞 +91-7290002168\n"
            "📧 info@ritzmediaworld.com"
        )
        yield {"answer": error_answer, "is_chunk": False, "final_answer": error_answer}


# ================= ROUTING =================

def _guard_condition(state: RAGState) -> str:
    return "ok"


# ================= GRAPH =================

def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("strict_guard", strict_guard_node)
    graph.add_node("generate", answer_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "strict_guard")
    graph.add_conditional_edges(
        "strict_guard",
        _guard_condition,
        {"reject": END, "ok": "generate"},
    )
    graph.add_edge("generate", END)

    return graph.compile()


rag_graph = build_rag_graph()


# ================= STREAMING GRAPH =================

def build_rag_graph_streaming():
    """
    Build a streaming version of the RAG graph.
    """
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("strict_guard", strict_guard_node)
    graph.add_node("generate", answer_node_streaming)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "strict_guard")
    graph.add_conditional_edges(
        "strict_guard",
        _guard_condition,
        {"reject": END, "ok": "generate"},
    )
    graph.add_edge("generate", END)

    return graph.compile()


rag_graph_streaming = build_rag_graph_streaming()
