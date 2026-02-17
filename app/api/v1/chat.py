# app/api/v1/chat.py
from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import run_chat

# Create a router for versioned API paths
router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """
    HTTP POST /v1/chat
    Body: { "message": "user question", "session_id": "optional" }

    It calls the RAG service and returns the final answer.
    """
    answer = run_chat(req.message)
    return ChatResponse(answer=answer)
