import redis
import os
from src.core.config import get_config
# Initialize Redis client with environment variables or default values
settings = get_config()

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)
