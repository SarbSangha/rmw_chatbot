# app/services/chat_service.py
"""
Service layer that:
- Receives a question string
- Calls the LangGraph RAG workflow
- Returns answer string
"""

import logging
import time

from app.rag.graph import rag_graph

logger = logging.getLogger(__name__)


def run_chat(question: str) -> dict:
    """
    Run the RAG graph for a single user question.
    Returns dict with 'answer' and 'has_answer' flag.
    """
    start = time.time()
    logger.info(f"📥 Question: {question[:80]}")

    state = {
        "question": question,
        "docs": [],
        "answer": "",
    }

    try:
        result_state = rag_graph.invoke(state)
        answer = result_state.get("answer", "").strip()
        # We intentionally do not return source metadata in responses.
        # The assistant should use Gemini/internal docs to craft answers,
        # but source links/snippets are not exposed to the user.

        elapsed = time.time() - start
        logger.info(f"⏱️ Total time: {elapsed:.2f}s")

        if not answer:
            return {
                "answer": (
                    "I couldn't find a specific answer for that.\n"
                    "Feel free to ask about our services, or contact us:\n"
                    "📞 +91-7290002168\n"
                    "📧 info@ritzmediaworld.com"
                ),
                "has_answer": False
            }

        return {
            "answer": answer,
            "has_answer": True
        }

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ RAG error after {elapsed:.2f}s: {str(e)}")
        return {
            "answer": (
                "I'm having trouble right now. Please contact us:\n"
                "📞 +91-7290002168\n"
                "📧 info@ritzmediaworld.com"
            ),
            "has_answer": False
        }
