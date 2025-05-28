import logging
import logging.config
import os
import queue
import sys
from contextvars import ContextVar
from logging import FileHandler, StreamHandler
from logging.handlers import QueueListener, QueueHandler
from typing import Any

# Constants
REQUEST_ID_VAR = ContextVar("request_id", default="system")
DEFAULT_LOG_LEVEL = "INFO"
VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
UVICORN_LOGGERS = ["uvicorn.error", "uvicorn.startup", "uvicorn.shutdown", "uvicorn.access"]
SQLALCHEMY_LOGGER_PREFIX = "sqlalchemy"

# Project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", os.path.join(PROJECT_ROOT, "logs"))
LOG_PATH = os.getenv("LOG_PATH", os.path.join(LOG_DIRECTORY, "app.log"))

# Ensure log directory exists
os.makedirs(LOG_DIRECTORY, exist_ok=True)

# Get log level from environment variable
LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
if LOG_LEVEL not in VALID_LOG_LEVELS:
    print(f"Invalid LOG_LEVEL: {LOG_LEVEL}. Defaulting to {DEFAULT_LOG_LEVEL}")
    LOG_LEVEL = DEFAULT_LOG_LEVEL

# Async log queue
log_queue = queue.Queue()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_VAR.get()
        return True


class SingleLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return original.replace("\n", " | ")



# Handlers
console_handler = StreamHandler()
console_handler.setFormatter(
    SingleLineFormatter("[%(asctime)s] [%(levelname)s | %(name)s] [%(request_id)s] %(message)s")
)

file_handler = FileHandler(LOG_PATH)
file_handler.setFormatter(
    SingleLineFormatter("[%(asctime)s] [%(levelname)s | %(name)s] [%(funcName)s] [%(request_id)s] %(message)s")
)

# Queue listener
listener = QueueListener(
    log_queue,
    console_handler,
    file_handler,
    respect_handler_level=True,
)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id_filter": {
            "()": RequestIdFilter,
        },
    },
    "handlers": {
        "queue_handler": {
            "class": "logging.handlers.QueueHandler",
            "queue": log_queue,
            "level": VALID_LOG_LEVELS[LOG_LEVEL],
            "filters": ["request_id_filter"],
        },
    },
    "loggers": {
        "": {  # root logger
            "level": VALID_LOG_LEVELS[LOG_LEVEL],
            "handlers": ["queue_handler"],
        },
        **{logger: {
            "level": VALID_LOG_LEVELS[LOG_LEVEL] if LOG_LEVEL == "DEBUG" else "WARNING",
            "handlers": ["queue_handler"],
            "propagate": False,
        } for logger in UVICORN_LOGGERS},
        SQLALCHEMY_LOGGER_PREFIX: {
            "level": VALID_LOG_LEVELS[LOG_LEVEL] if LOG_LEVEL == "DEBUG" else "WARNING",
            "handlers": ["queue_handler"],
            "propagate": False,
        },
    },
}

# Initialize logging
try:
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level: {LOG_LEVEL}")
    listener.start()
except Exception as e:
    print(f"Could not configure logging. Error: {e}. Defaulting to console logging.")
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error("Fallback to basic console logging.")

async def shutdown_logging() -> None:
    """Gracefully shutdown logging when the application stops."""
    listener.stop()
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except queue.Empty:
            break
