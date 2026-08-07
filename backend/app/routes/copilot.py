from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from backend.app.database import get_session
from backend.app.services.copilot_service import copilot_service

router = APIRouter(prefix="/copilot", tags=["copilot"])

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
def chat_copilot(req: ChatRequest, session: Session = Depends(get_session)):
    """AI Copilot natural language endpoint for dispute operations."""
    reply = copilot_service.process_query(req.query, session)
    return ChatResponse(reply=reply)
