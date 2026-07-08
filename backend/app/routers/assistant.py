from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import assistant as svc


class ChatRequest(BaseModel):
    message: str


router = APIRouter(prefix="/api", tags=["assistant"])


@router.get("/assistant/status")
def status():
    return {"enabled": svc.is_enabled(), "model": svc.MODEL}


@router.post("/assistant/chat")
def chat(req: ChatRequest):
    try:
        return svc.chat(req.message)
    except svc.AssistantDisabled:
        raise HTTPException(501, "assistant disabled")
