from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.core.redis import redis_client
from firebase_admin import auth
import uuid

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register_user(req: LoginRequest):
    try:
        user = auth.create_user(email=req.email, password=req.password)
        return {"message": "User created", "uid": user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login_user(req: LoginRequest):
    # In production, use Firebase ID Token verification with frontend
    # Here for demo purposes we generate a fake session token
    try:
        user = auth.get_user_by_email(req.email)
        session_token = str(uuid.uuid4())
        redis_client.setex(f"session:{session_token}", 3600 * 24, user.uid)
        return {"session_token": session_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(session_token: str):
    redis_client.delete(f"session:{session_token}")
    return {"message": "Logged out"}
