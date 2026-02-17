# app/models/chat.py
from pydantic import BaseModel


class ChatRequest(BaseModel):
    # Optional session_id field (for future multi-turn, memory, etc.)
    session_id: str | None = None
    # User question text
    message: str


class ChatResponse(BaseModel):
    # Final answer text
    answer: str
