import logging
import os
import sys

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Import your custom logger
from src.core.logger import Logger, get_logger, set_global_context, set_default_config

# Basic logger for this config module only
_config_logger = logging.getLogger(__name__)

try:
    load_dotenv()
except Exception as e:
    logging.fatal(f"Could not load .env file. Error: {e}. Shutting down the app.")
    sys.exit(1)

class Config(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "")
    VERSION: str = os.getenv("VERSION", "")
    ENV: str = os.getenv("ENV", "prod")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_DIRECTORY: str = os.getenv("LOG_DIRECTORY", "logs")
    LOG_FILE_NAME: str = os.getenv("LOG_FILE_NAME", "app.log")
    LOG_COLOR: bool = os.getenv("LOG_COLOR", "True").lower() == "true"
    LOG_ENABLE_CONSOLE: bool = os.getenv("LOG_ENABLE_CONSOLE", "True").lower() == "true"
    LOG_ENABLE_FILE: bool = os.getenv("LOG_ENABLE_FILE", "True").lower() == "true"
    LOG_MAX_FILE_SIZE: int = int(os.getenv("LOG_MAX_FILE_SIZE", "10485760"))  # 10MB default
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_ASYNC_WORKERS: int = int(os.getenv("LOG_ASYNC_WORKERS", "2"))
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

settings = get_config()
# Set default configuration for all logger instances
try:
    set_default_config(
        log_level=settings.LOG_LEVEL,
        log_directory=settings.LOG_DIRECTORY,
        log_filename=settings.LOG_FILE_NAME,
        use_colors=settings.LOG_COLOR,
        enable_console=settings.LOG_ENABLE_CONSOLE,
        enable_file=settings.LOG_ENABLE_FILE,
        max_file_size=settings.LOG_MAX_FILE_SIZE,
        backup_count=settings.LOG_BACKUP_COUNT,
        async_workers=settings.LOG_ASYNC_WORKERS
    )
    
    # Set global context that will be available in all log messages
    set_global_context(
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        environment=settings.ENV
    )
    
    # Configure the main application logger (singleton)
    logger = get_logger(name=__name__)
    
    # Log successful initialization
    logger.info(f"Logger configured successfully for {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENV}, Log Level: {settings.LOG_LEVEL}")
    logger.debug(f"Log Directory: {settings.LOG_DIRECTORY}, Log File: {settings.LOG_FILE_NAME}")
    
except Exception as e:
    _config_logger.error(f"Failed to configure custom logger: {e}")
    _config_logger.error("Falling back to basic logging")
    # Fallback to basic logging if custom logger fails
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"{settings.LOG_DIRECTORY}/{settings.LOG_FILE_NAME}")
        ]
    )
    logger = logging.getLogger("app")