from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.core.redis import redis_client
from firebase_admin import auth
import uuid
from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register_user(req: RegisterRequest):
    logger.debug(f"Attempting to register user with email: {req.email}, username: {req.username}")
    try:
        # Check if username already exists
        if redis_client.exists(f"username:{req.username}"):
            logger.debug(f"Username {req.username} already exists")
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create user in Firebase
        user = auth.create_user(email=req.email, password=req.password)
        logger.debug(f"User created with UID: {user.uid}")
        
        # Store username mapping in Redis
        redis_client.set(f"user:{user.uid}:username", req.username)
        redis_client.set(f"username:{req.username}", user.uid)
        
        logger.debug(f"Username {req.username} mapped to UID: {user.uid}")
        return {"message": "User created", "uid": user.uid, "username": req.username}
    except HTTPException:
        raise
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
        
        # Store session with user ID
        redis_client.setex(f"session:{session_token}", 3600 * 24, user.uid)
        
        # Get username for response
        username = redis_client.get(f"user:{user.uid}:username")
        
        logger.debug(f"Login successful for {req.email}, session_token: {session_token}, username: {username}")
        return {"session_token": session_token, "username": username}
    except Exception as e:
        logger.debug(f"Login failed for {req.email}: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(session_token: str):
    logger.debug(f"Logging out session_token: {session_token}")
    redis_client.delete(f"session:{session_token}")
    logger.debug(f"Session {session_token} deleted from Redis")
    return {"message": "Logged out"}