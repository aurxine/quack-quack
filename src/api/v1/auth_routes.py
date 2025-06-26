from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.core.redis import redis_client
from firebase_admin import auth
import uuid
from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register_user(req: LoginRequest):
    logger.debug(f"Attempting to register user with email: {req.email}")
    try:
        user = auth.create_user(email=req.email, password=req.password)
        logger.debug(f"User created with UID: {user.uid}")
        return {"message": "User created", "uid": user.uid}
    except Exception as e:
        logger.debug(f"Registration failed for email {req.email}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login_user(req: LoginRequest):
    logger.debug(f"Attempting login for email: {req.email}")
    try:
        user = auth.get_user_by_email(req.email)
        session_token = str(uuid.uuid4())
        logger.set_context(request_id = session_token)
        redis_client.setex(f"session:{session_token}", 3600 * 24, user.uid)
        logger.debug(f"Login successful for {req.email}, session_token: {session_token}")
        return {"session_token": session_token}
    except Exception as e:
        logger.debug(f"Login failed for {req.email}: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(session_token: str):
    logger.debug(f"Logging out session_token: {session_token}")
    redis_client.delete(f"session:{session_token}")
    logger.debug(f"Session {session_token} deleted from Redis")
    return {"message": "Logged out"}
