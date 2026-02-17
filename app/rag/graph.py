# app/rag/graph.py
"""
Defines the LangGraph RAG workflow with strict behavior:
- Retrieve relevant chunks
- If nothing relevant, return fixed message
- Otherwise, ask LLM to answer using only context
"""

from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from app.rag.vectorstore import get_retriever
from app.rag.prompts import STRICT_RAG_PROMPT
from app.core.config import settings


class RAGState(TypedDict):
    # The user's question
    question: str
    # Documents retrieved from vector DB
    docs: List[Document]
    # Final answer text to return
    answer: str


# Create shared LLM and retriever instances
_llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4o-mini",  # choose your model
)
_retriever = get_retriever(k=4)


def retrieve_node(state: RAGState) -> RAGState:
    docs = _retriever.invoke(state["question"])  # ✅ NEW
    return {**state, "docs": docs}



def strict_guard_node(state: RAGState) -> RAGState:
    """
    Only reject if ZERO documents found. Otherwise let LLM handle with context.
    """
    if len(state["docs"]) == 0:
        return {
            **state,
            "answer": "I can only help with information from our agency documents. Ask me about our services, team, location, or capabilities!"
        }
    return state  # Let LLM answer if ANY docs found



def answer_node(state: RAGState) -> RAGState:
    """
    Node 3: Use the LLM to generate an answer from the retrieved docs.
    - If 'answer' is already set (from strict_guard_node), we just return.
    """
    # If strict_guard_node already decided answer, skip LLM
    if state.get("answer"):
        return state

    # Concatenate contents of retrieved docs as context
    context = "\n\n".join(doc.page_content for doc in state["docs"])

    # Build messages for the chat LLM using our strict prompt
    messages = STRICT_RAG_PROMPT.format_messages(
        context=context,
        question=state["question"],
    )

    # Call LLM
    resp = _llm.invoke(messages)

    # Save answer in state and return
    return {**state, "answer": resp.content}


def _guard_condition(state: RAGState) -> str:
    """
    Condition function used by LangGraph to decide next step:
    - If 'answer' already exists (i.e., strict_guard_node rejected), go to END.
    - Otherwise, go to 'answer' node.
    """
    return "reject" if state.get("answer") else "ok"


def build_rag_graph():
    """
    Build and compile the RAG graph.
    """
    graph = StateGraph(RAGState)

    # Register nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("strict_guard", strict_guard_node)
    graph.add_node("answer", answer_node)

    # Entry point: start at retrieve
    graph.set_entry_point("retrieve")

    # After retrieve -> go to strict_guard
    graph.add_edge("retrieve", "strict_guard")

    # From strict_guard -> either END or answer, based on condition
    graph.add_conditional_edges(
        "strict_guard",
        _guard_condition,
        {
            "reject": END,      # if reject, stop with existing answer
            "ok": "answer",     # otherwise, go to answer node
        },
    )

    # After answer -> END
    graph.add_edge("answer", END)

    # Compile graph to a runnable object
    return graph.compile()


# Single compiled graph instance to import elsewhere
rag_graph = build_rag_graph()
