from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from database import connect_to_mongo, close_mongo_connection, mongo_db
from schema import Prompt, Conversation, ConversationMessage
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store chat prompt
chat_prompt_template = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global chat_prompt_template
    logger.info("🚀 Starting up AI Student Chatbot API...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Load chat prompt from database
    try:
        async with mongo_db() as db:
            chat_prompt = await db.chat_prompt.find_one(
                {"name": "chat_prompt"}
            )
            if chat_prompt:
                chat_prompt_template = chat_prompt["prompt"]
                logger.info("✅ Loaded chat prompt template from database.")
            else:
                logger.error("❌ No chat prompt found in the database!")
                raise Exception("Chat prompt not found in database")
    except Exception as e:
        logger.error(f"❌ Error loading chat prompt: {e}")
        raise Exception(f"Failed to load chat prompt: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Student Chatbot API...")
    await close_mongo_connection()

app = FastAPI(
    title="AI Student Chatbot API", 
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure OpenAI
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

# Initialize client
client = get_openai_client()

# Conversation management functions
async def get_or_create_conversation(session_id: str):
    """Get existing conversation or create new one"""
    async with mongo_db() as db:
        conversation = await db.conversations.find_one({"session_id": session_id})
        if not conversation:
            # Create new conversation
            new_conversation = {
                "session_id": session_id,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await db.conversations.insert_one(new_conversation)
            conversation = await db.conversations.find_one({"_id": result.inserted_id})
        return conversation

async def add_message_to_conversation(session_id: str, role: str, content: str):
    """Add a message to the conversation"""
    async with mongo_db() as db:
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        await db.conversations.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

async def get_conversation_history(session_id: str, limit: int = 10):
    """Get recent conversation history for context"""
    async with mongo_db() as db:
        conversation = await db.conversations.find_one({"session_id": session_id})
        if conversation and "messages" in conversation:
            # Return last 'limit' messages for context
            messages = conversation["messages"][-limit:]
            return messages
        return []

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.get("/")
async def root():
    return {"message": "AI Student Chatbot API is running!"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Use the loaded chat prompt template
        if not chat_prompt_template:
            raise HTTPException(status_code=500, detail="System prompt not loaded from database")
        
        # Generate or use provided session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get or create conversation
        await get_or_create_conversation(session_id)
        
        # Get conversation history for context
        history = await get_conversation_history(session_id, limit=10)
        
        # Build messages for OpenAI API
        messages = [{"role": "system", "content": chat_prompt_template}]
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Make request to OpenAI with full conversation context
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        assistant_response = response.choices[0].message.content.strip()
        
        # Save both user message and assistant response to conversation
        await add_message_to_conversation(session_id, "user", request.message)
        await add_message_to_conversation(session_id, "assistant", assistant_response)
        
        return ChatResponse(response=assistant_response, session_id=session_id)
    
    except Exception as e:
        # Handle all OpenAI errors and other exceptions
        error_message = str(e)
        if "authentication" in error_message.lower():
            raise HTTPException(status_code=401, detail="Invalid OpenAI API key")
        elif "rate limit" in error_message.lower():
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        elif "api" in error_message.lower():
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {error_message}")
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {error_message}")

@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history for a session"""
    try:
        history = await get_conversation_history(session_id, limit=50)
        return {"session_id": session_id, "messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

@app.post("/conversations/new")
async def new_conversation():
    """Start a new conversation"""
    session_id = str(uuid.uuid4())
    await get_or_create_conversation(session_id)
    return {"session_id": session_id, "message": "New conversation started"}

@app.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str):
    """Delete a conversation"""
    try:
        async with mongo_db() as db:
            result = await db.conversations.delete_one({"session_id": session_id})
            if result.deleted_count > 0:
                return {"message": "Conversation deleted successfully"}
            else:
                raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
