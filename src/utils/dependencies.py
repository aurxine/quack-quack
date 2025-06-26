from fastapi import Header, HTTPException
from src.core.redis import redis_client

async def get_current_user(session_token: str = Header(...)):
    user_id = redis_client.get(f"session:{session_token}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user_id
