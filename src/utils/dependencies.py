from fastapi import Header, HTTPException
from src.core.redis import redis_client
from src.core.logger import get_logger
logger = get_logger(__name__)

async def get_current_user(session_token: str = Header(...)):
    user_id = redis_client.get(f"session:{session_token}")
    logger.debug(f"Retrieved user_id: {user_id} for session_token: {session_token}")
    if not user_id:
        logger.warning(f"Invalid or expired session for token: {session_token}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user_id
