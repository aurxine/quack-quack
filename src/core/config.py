import logging
import os
import sys

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

from src.core.logger import logger

logger = logging.getLogger(__name__)

try:
    load_dotenv()
except Exception as e:
    logging.fatal(f"Could not load .env file. Error: {e}. Shutting down the app.")
    sys.exit(1)

class Config(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "")
    VERSION: str = os.getenv("VERSION", "")
    ENV: str = os.getenv("ENV", "prod")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    

def get_config() -> Config:
    return Config()