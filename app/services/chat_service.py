# app/services/chat_service.py
"""
Service layer that:
- Receives a question string
- Calls the LangGraph RAG workflow
- Returns answer string
"""

from app.rag.graph import rag_graph


def run_chat(question: str) -> str:
    """
    Run the RAG graph for a single user question.
    For now, this is stateless (no history).
    """
    # Initial graph state
    state = {
        "question": question,
        "docs": [],
        "answer": "",
    }

    # Invoke the LangGraph workflow synchronously
    result_state = rag_graph.invoke(state)

    # Extract final answer from state
    return result_state["answer"]
