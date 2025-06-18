import logging
import os
import sys

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

from src.core.logger import logger


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
    BASE_URL: str = os.getenv(f"BASE_URL_{os.getenv('ENV', 'prod')}", "/")
    SWAGGER_USERNAME: str = os.getenv("SWAGGER_USERNAME", "")
    SWAGGER_PASSWORD: str = os.getenv("SWAGGER_PASSWORD", "")

    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")


    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    def __str__(self):
        return (
            f"Config("
            f"APP_NAME={self.APP_NAME!r}, "
            f"VERSION={self.VERSION!r}, "
            f"ENV={self.ENV!r}, "
            f"LOG_LEVEL={self.LOG_LEVEL!r}, "
            f"BASE_URL={self.BASE_URL!r}, "
            f"SWAGGER_USERNAME={self.SWAGGER_USERNAME!r}, "
            f"SWAGGER_PASSWORD={'***' if self.SWAGGER_PASSWORD else ''}"
            f")"
        )

    def __repr__(self):
        return self.__str__()
    

def get_config() -> Config:
    return Config()