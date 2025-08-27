from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId


class Prompt(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str = Field(...)
    prompt: str = Field(...)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ConversationMessage(BaseModel):
    role: str = Field(...)  # "user" or "assistant"
    content: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    session_id: str = Field(...)
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
