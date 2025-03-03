from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    content: str
    type: str

class ChatRequest(BaseModel):
    content: str
    type: str
    sessionId: Optional[str] = None

class ChatResponse(BaseModel):
    messages: List[Message]
    sessionId: str
    
class ChatCreateRequest(BaseModel):
    sessionId: str
    title: str = "Nueva conversación"

class ChatUpdateRequest(BaseModel):
    title: str

class MessageRequest(BaseModel):
    content: str
    type: str = "Human"