import os
import asyncio
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ai_chatbot")

# Global client variable
mongo_client = None


async def connect_to_mongo():
    """Initialize MongoDB connection"""
    global mongo_client
    try:
        mongo_client = AsyncIOMotorClient(MONGODB_URL)
        # Test the connection
        await mongo_client.admin.command('ping')
        logger.info(f"✅ Connected to MongoDB at {MONGODB_URL}")
        return mongo_client
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("🔌 Disconnected from MongoDB")


@asynccontextmanager
async def mongo_db():
    """Context manager for database operations"""
    global mongo_client
    if not mongo_client:
        await connect_to_mongo()
    
    try:
        db = mongo_client[DATABASE_NAME]
        yield db
    except Exception as e:
        logger.error(f"Database operation error: {e}")
        raise


def get_database():
    """Get database instance (synchronous helper)"""
    global mongo_client
    if not mongo_client:
        raise RuntimeError("MongoDB client not initialized. Call connect_to_mongo() first.")
    return mongo_client[DATABASE_NAME]
