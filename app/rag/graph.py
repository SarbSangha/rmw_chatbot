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


# ✅ LangChain wrapper with max_retries=0
_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0,
    max_output_tokens=400,
    top_p=0.8,
    top_k=40,
    convert_system_message_to_human=True,
    max_retries=0,        # ✅ No retrying
    request_timeout=10,    # ✅ Hard 6s timeout
)

_retriever = get_retriever(k=3)


# ================= NODES =================

def retrieve_node(state: RAGState) -> RAGState:
    try:
        docs = _retriever.invoke(state["question"])
        logger.info(f"📚 Retrieved {len(docs)} docs for: {state['question'][:50]}")
        return {**state, "docs": docs}
    except Exception as e:
        logger.error(f"❌ Retrieval error: {e}")
        return {**state, "docs": []}


def strict_guard_node(state: RAGState) -> RAGState:
    if len(state["docs"]) == 0:
        return {
            **state,
            "answer": (
                "I can only help with information about Ritz Media World. "
                "Ask me about our services, team, or capabilities! 😊"
            )
        }
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

        if not answer_text:
            answer_text = (
                "Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            )

        logger.info(f"✅ Answer ready ({len(answer_text)} chars)")
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
    return "reject" if state.get("answer") else "ok"


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
