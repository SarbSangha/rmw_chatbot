# app/rag/graph.py
import logging
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from app.rag.vectorstore import get_retriever
from app.rag.prompts import STRICT_RAG_PROMPT
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGState(TypedDict):
    question: str
    docs: List[Document]
    answer: str


# ✅ LangChain wrapper with optimized parameters for direct responses
_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.3,  # Slightly higher to avoid over-cautious responses
    max_output_tokens=500,  # Increased for better answers
    top_p=0.95,  # More permissive
    top_k=40,
    convert_system_message_to_human=True,
    max_retries=0,
    request_timeout=10,
)

_retriever = get_retriever(k=3)


# ================= NODES =================

def retrieve_node(state: RAGState) -> RAGState:
    try:
        # Fetch internal docs from vectorstore only (no web retrieval)
        docs = _retriever.invoke(state["question"]) or []
        logger.info(f"📚 Retrieved {len(docs)} internal docs for: {state['question'][:50]}")
        return {**state, "docs": list(docs)}
    except Exception as e:
        logger.error(f"❌ Retrieval error: {e}")
        return {**state, "docs": []}


def strict_guard_node(state: RAGState) -> RAGState:
    # Previously this node blocked generation when no docs were found.
    # Allow generation in all cases so web snippets or the model's knowledge
    # can be used to craft a professional answer.
    return state


def answer_node(state: RAGState) -> RAGState:
    if state.get("answer"):
        return state

    try:
        context_parts = [doc.page_content[:1500] for doc in state["docs"][:3]]
        context = "\n\n".join(context_parts)

        messages = STRICT_RAG_PROMPT.format_messages(
            context=context,
            question=state["question"],
        )

        logger.info(f"🤖 Calling Gemini for: {state['question'][:50]}")
        resp = _llm.invoke(messages)

        # Parse response
        if hasattr(resp, 'content'):
            if isinstance(resp.content, list):
                answer_text = resp.content[0].get('text', '') if resp.content else ""
            elif isinstance(resp.content, str):
                answer_text = resp.content
            else:
                answer_text = str(resp.content)
        else:
            answer_text = str(resp)

        answer_text = answer_text.strip()
        
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


# ================= ROUTING =================

def _guard_condition(state: RAGState) -> str:
    # Always proceed to generation; the answer node will handle empty context.
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
