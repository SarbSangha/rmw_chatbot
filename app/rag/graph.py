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
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
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
_llm = ChatGoogleGenerativeAI(
    # model="gemini-pro",  # ✅ Free tier compatible
    model="gemini-3-flash-preview",  # ✅ Free tier compatible
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0
)


_retriever = get_retriever(k=4)

def retrieve_node(state: RAGState) -> RAGState:
    docs = _retriever.invoke(state["question"])
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

    # ✅ FIX: Robust response parsing
    try:
        if hasattr(resp, 'content'):
            if isinstance(resp.content, list):
                # New format: list of content parts
                answer_text = resp.content[0].get('text', '') if resp.content else "I couldn't generate an answer."
            elif isinstance(resp.content, str):
                # Old format: direct string
                answer_text = resp.content
            else:
                answer_text = str(resp.content)
        else:
            answer_text = str(resp)
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        answer_text = "I encountered an error processing the response."

    # Save answer in state and return
    return {**state, "answer": answer_text}


def _guard_condition(state: RAGState) -> str:
    """
    Condition function used by LangGraph to decide next step:
    - If 'answer' already exists (i.e., strict_guard_node rejected), go to END.
    - Otherwise, go to 'generate' node.
    """
    return "reject" if state.get("answer") else "ok"

def build_rag_graph():
    """
    Build and compile the RAG graph.
    """
    graph = StateGraph(RAGState)

    # Register nodes (FIXED: "generate" instead of "answer")
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("strict_guard", strict_guard_node)
    graph.add_node("generate", answer_node)  # FIXED: Unique name

    # Entry point: start at retrieve
    graph.set_entry_point("retrieve")

    # After retrieve -> go to strict_guard
    graph.add_edge("retrieve", "strict_guard")

    # From strict_guard -> either END or generate, based on condition
    graph.add_conditional_edges(
        "strict_guard",
        _guard_condition,
        {
            "reject": END,      # if reject, stop with existing answer
            "ok": "generate",   # FIXED: Match new node name
        },
    )

    # After generate -> END
    graph.add_edge("generate", END)  # FIXED: Match new node name

    # Compile graph to a runnable object
    return graph.compile()

# Single compiled graph instance to import elsewhere
rag_graph = build_rag_graph()
