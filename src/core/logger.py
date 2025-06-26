"""
Advanced Asynchronous Logger with Context Management
Follows industry best practices for enterprise logging
"""

import asyncio
import logging
import logging.handlers
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar, copy_context
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json
import traceback
from enum import Enum
import asyncio


class LogLevel(Enum):
    """Log level enumeration for type safety"""
    CRITICAL = logging.CRITICAL
    FATAL = logging.FATAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET


class ColorCodes:
    """ANSI color codes for console output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    LEVEL_COLORS = {
        logging.DEBUG: ColorCodes.CYAN,
        logging.INFO: ColorCodes.GREEN,
        logging.WARNING: ColorCodes.YELLOW,
        logging.ERROR: ColorCodes.RED,
        logging.CRITICAL: ColorCodes.BRIGHT_RED + ColorCodes.BOLD,
    }
    
    def __init__(self, fmt: str, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.fmt = fmt
        
    def format(self, record: logging.LogRecord) -> str:
        # Add context variables to record - ensure all expected fields exist
        context_data = LoggerContext.get_all_context()
        
        # Extract format field names from the format string
        import re
        format_fields = re.findall(r'%\((\w+)\)s', self.fmt)
        
        # Ensure all format fields exist in the record
        for field in format_fields:
            if not hasattr(record, field):
                # Set to context value if available, otherwise empty string
                setattr(record, field, context_data.get(field, ''))
        
        # Add any additional context data
        for key, value in context_data.items():
            if not hasattr(record, key):
                setattr(record, key, value)
            
        # Format the message
        formatter = logging.Formatter(self.fmt)
        message = formatter.format(record)
        
        # Apply colors if enabled and writing to console
        if self.use_colors and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.LEVEL_COLORS.get(record.levelno, '')
            return f"{color}{message}{ColorCodes.RESET}"
        
        return message


class SafeFormatter(logging.Formatter):
    """Safe formatter that handles missing context fields gracefully"""
    
    def __init__(self, fmt: str, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        
    def format(self, record: logging.LogRecord) -> str:
        # Add context variables to record - ensure all expected fields exist
        context_data = LoggerContext.get_all_context()
        
        # Extract format field names from the format string
        import re
        fmt_str = self._fmt if self._fmt is not None else ""
        format_fields = re.findall(r'%\((\w+)\)s', fmt_str)
        
        # Ensure all format fields exist in the record
        for field in format_fields:
            if not hasattr(record, field):
                # Set to context value if available, otherwise empty string
                setattr(record, field, context_data.get(field, ''))
        
        # Add any additional context data
        for key, value in context_data.items():
            if not hasattr(record, key):
                setattr(record, key, value)
            
        return super().format(record)


class LoggerContext:
    """Context manager for logger variables using contextvars"""
    
    _context_vars: Dict[str, ContextVar] = {}
    _lock = threading.Lock()
    
    @classmethod
    def set_context(cls, key: str, value: Any) -> None:
        """Set context variable"""
        with cls._lock:
            if key not in cls._context_vars:
                cls._context_vars[key] = ContextVar(key, default='')
            cls._context_vars[key].set(str(value))
    
    @classmethod
    def get_context(cls, key: str) -> str:
        """Get context variable value"""
        with cls._lock:
            if key in cls._context_vars:
                return cls._context_vars[key].get('')
            return ''
    
    @classmethod
    def get_all_context(cls) -> Dict[str, str]:
        """Get all context variables"""
        result = {}
        with cls._lock:
            for key, var in cls._context_vars.items():
                value = var.get('')
                # Include all values, even empty ones, to ensure format fields exist
                result[key] = value
        return result
    
    @classmethod
    def clear_context(cls, key: Optional[str] = None) -> None:
        """Clear specific context variable or all if no key provided"""
        with cls._lock:
            if key and key in cls._context_vars:
                cls._context_vars[key].set('')
            elif key is None:
                for var in cls._context_vars.values():
                    var.set('')


class AsyncLogHandler:
    """Asynchronous log handler to prevent blocking main thread"""
    
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AsyncLogger")
        self._shutdown = False
    
    def emit_async(self, handler: logging.Handler, record: logging.LogRecord) -> None:
        """Emit log record asynchronously"""
        if not self._shutdown:
            future = self.executor.submit(self._emit_sync, handler, record)
            # Don't wait for completion to maintain async behavior
            future.add_done_callback(self._handle_emit_error)
    
    def _emit_sync(self, handler: logging.Handler, record: logging.LogRecord) -> None:
        """Synchronous emit wrapper"""
        try:
            handler.emit(record)
        except Exception as e:
            # Fallback error handling
            print(f"Logger error: {e}", file=sys.stderr)
    
    def _handle_emit_error(self, future) -> None:
        """Handle errors from async emit"""
        try:
            future.result()
        except Exception as e:
            print(f"Async logging error: {e}", file=sys.stderr)
    
    def shutdown(self) -> None:
        """Shutdown the async handler"""
        self._shutdown = True
        self.executor.shutdown(wait=True)


class AsyncLoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for async logging"""
    
    def __init__(self, logger: logging.Logger, async_handler: AsyncLogHandler):
        super().__init__(logger, {})
        self.async_handler = async_handler
        
    def _process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with context"""
        return str(msg), kwargs
        
    def _log_async(self, level: int, msg: Any, args: tuple, **kwargs) -> None:
        """Asynchronous logging method"""
        if self.isEnabledFor(level):
            # Get caller information for better logging context
            import inspect
            frame = inspect.currentframe()
            try:
                # Go up the call stack to find the actual caller
                # Skip: _log_async -> debug/info/warning/error -> actual caller
                caller_frame = frame.f_back.f_back.f_back # type: ignore
                if caller_frame:
                    filename = caller_frame.f_code.co_filename
                    lineno = caller_frame.f_lineno
                    funcname = caller_frame.f_code.co_name
                else:
                    filename = "(unknown file)"
                    lineno = 0
                    funcname = "(unknown function)"
            finally:
                del frame
            
            record = self.logger.makeRecord(
                self.logger.name, level, filename, lineno, 
                msg, args, None, func=funcname, **kwargs
            )
            
            # Add context to record - ensure all expected fields exist
            context_data = LoggerContext.get_all_context()
            for key, value in context_data.items():
                setattr(record, key, value)
            
            # Emit to all handlers asynchronously
            for handler in self.logger.handlers:
                if hasattr(self.async_handler, 'emit_async'):
                    self.async_handler.emit_async(handler, record)
    
    def debug(self, msg: Any, *args, **kwargs) -> None:
        self._log_async(logging.DEBUG, msg, args, **kwargs)
        
    def info(self, msg: Any, *args, **kwargs) -> None:
        self._log_async(logging.INFO, msg, args, **kwargs)
        
    def warning(self, msg: Any, *args, **kwargs) -> None:
        self._log_async(logging.WARNING, msg, args, **kwargs)
        
    def error(self, msg: Any, *args, **kwargs) -> None:
        self._log_async(logging.ERROR, msg, args, **kwargs)
        
    def critical(self, msg: Any, *args, **kwargs) -> None:
        self._log_async(logging.CRITICAL, msg, args, **kwargs)
        
    def exception(self, msg: Any, *args, **kwargs) -> None:
        """Log exception with traceback"""
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)


class Logger:
    """
    Advanced Logger class with async capabilities, context management,
    and industry best practices implementation.
    """
    
    DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s | %(name)s] [%(funcName)s] [%(request_id)s] %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    _instances: Dict[str, 'Logger'] = {}
    _default_config: Optional[Dict[str, Any]] = None
    _lock = threading.Lock()
    
    def __init__(
        self,
        name: str = "app",
        log_level: Union[str, int, LogLevel] = LogLevel.INFO,
        log_directory: str = "logs",
        log_filename: str = "app.log",
        log_format: str = DEFAULT_FORMAT,
        date_format: str = DEFAULT_DATE_FORMAT,
        use_colors: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_console: bool = True,
        enable_file: bool = True,
        async_workers: int = 2
    ):
        self.name = name
        self.log_level = self._parse_log_level(log_level)
        self.log_directory = Path(log_directory)
        self.log_filename = log_filename
        self.log_format = log_format
        self.date_format = date_format
        self.use_colors = use_colors
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        
        # Initialize async handler
        self.async_handler = AsyncLogHandler(max_workers=async_workers)
        
        # Initialize logger
        self._logger = self._setup_logger()
        self._async_adapter = AsyncLoggerAdapter(self._logger, self.async_handler)
        
    @classmethod
    def set_default_config(cls, **config) -> None:
        """Set default configuration for all new logger instances"""
        cls._default_config = config
    
    @classmethod
    def get_logger(cls, name: str = "app", **kwargs) -> 'Logger':
        """Singleton pattern for logger instances with config inheritance"""
        with cls._lock:
            if name not in cls._instances:
                # Use default config if available, then override with any provided kwargs
                final_config = {}
                if cls._default_config:
                    final_config.update(cls._default_config)
                final_config.update(kwargs)
                final_config['name'] = name  # Always use the provided name
                
                cls._instances[name] = cls(**final_config)
            return cls._instances[name]
    
    def _parse_log_level(self, level: Union[str, int, LogLevel]) -> int:
        """Parse log level from various input types"""
        if isinstance(level, LogLevel):
            return level.value
        elif isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        elif isinstance(level, int):
            return level
        else:
            return logging.INFO
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the logger with handlers and formatters"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers to prevent duplicates
        logger.handlers.clear()
        
        # Create formatters
        file_formatter = SafeFormatter(
            self.log_format, 
            datefmt=self.date_format
        )
        console_formatter = ColoredFormatter(
            self.log_format, 
            use_colors=self.use_colors
        )
        
        # Setup file handler
        if self.enable_file:
            try:
                self.log_directory.mkdir(parents=True, exist_ok=True)
                log_file_path = self.log_directory / self.log_filename
                
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file_path,
                    maxBytes=self.max_file_size,
                    backupCount=self.backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(self.log_level)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
                
            except Exception as e:
                print(f"Failed to setup file logging: {e}", file=sys.stderr)
        
        # Setup console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def set_context(self, **kwargs) -> None:
        """Set context variables for logging"""
        for key, value in kwargs.items():
            LoggerContext.set_context(key, value)
    
    def clear_context(self, key: Optional[str] = None) -> None:
        """Clear context variables"""
        LoggerContext.clear_context(key)
    
    def get_context(self, key: str) -> str:
        """Get context variable value"""
        return LoggerContext.get_context(key)
    
    def set_level(self, level: Union[str, int, LogLevel]) -> None:
        """Set logging level"""
        self.log_level = self._parse_log_level(level)
        self._logger.setLevel(self.log_level)
        for handler in self._logger.handlers:
            handler.setLevel(self.log_level)
    
    def debug(self, message: Any, **kwargs) -> None:
        """Log debug message"""
        self._async_adapter.debug(message, **kwargs)
    
    def info(self, message: Any, **kwargs) -> None:
        """Log info message"""
        self._async_adapter.info(message, **kwargs)
    
    def warning(self, message: Any, **kwargs) -> None:
        """Log warning message"""
        self._async_adapter.warning(message, **kwargs)
    
    def warn(self, message: Any, **kwargs) -> None:
        """Alias for warning"""
        self.warning(message, **kwargs)
    
    def error(self, message: Any, **kwargs) -> None:
        """Log error message"""
        self._async_adapter.error(message, **kwargs)
    
    def critical(self, message: Any, **kwargs) -> None:
        """Log critical message"""
        self._async_adapter.critical(message, **kwargs)
    
    def fatal(self, message: Any, **kwargs) -> None:
        """Alias for critical"""
        self.critical(message, **kwargs)
    
    def exception(self, message: Any, **kwargs) -> None:
        """Log exception with traceback"""
        self._async_adapter.exception(message, **kwargs)
    
    def log_structured(self, level: Union[str, int, LogLevel], data: Dict[str, Any]) -> None:
        """Log structured data as JSON"""
        level_int = self._parse_log_level(level)
        json_data = json.dumps(data, default=str, ensure_ascii=False)
        self._async_adapter._log_async(level_int, json_data, ())
    
    def log_with_context(
        self, 
        level: Union[str, int, LogLevel], 
        message: Any, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log message with temporary context"""
        old_context = {}
        if context:
            # Save current context
            old_context = LoggerContext.get_all_context()
            
            # Set new context
            for key, value in context.items():
                LoggerContext.set_context(key, value)
        
        try:
            level_int = self._parse_log_level(level)
            self._async_adapter._log_async(level_int, message, (), **kwargs)
        finally:
            if context:
                # Restore old context
                LoggerContext.clear_context()
                for key, value in old_context.items():
                    LoggerContext.set_context(key, value)
    
    def get_child_logger(self, suffix: str) -> 'Logger':
        """Create a child logger"""
        child_name = f"{self.name}.{suffix}"
        return self.__class__.get_logger(
            name=child_name,
            log_level=self.log_level,
            log_directory=str(self.log_directory),
            log_filename=self.log_filename,
            log_format=self.log_format,
            date_format=self.date_format,
            use_colors=self.use_colors,
            max_file_size=self.max_file_size,
            backup_count=self.backup_count,
            enable_console=self.enable_console,
            enable_file=self.enable_file
        )
    
    def shutdown(self) -> None:
        """Shutdown the logger gracefully"""
        self.async_handler.shutdown()
        
        # Close all handlers
        for handler in self._logger.handlers:
            try:
                handler.close()
            except Exception:
                pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()


# Convenience functions for quick access
def get_logger(name: str = "app", **kwargs) -> Logger:
    """Get logger instance"""
    return Logger.get_logger(name, **kwargs)


def set_default_config(**config) -> None:
    """Set default configuration that will be used for all new logger instances"""
    Logger.set_default_config(**config)


def set_global_context(**kwargs) -> None:
    """Set global context variables"""
    for key, value in kwargs.items():
        LoggerContext.set_context(key, value)


def clear_global_context(key: Optional[str] = None) -> None:
    """Clear global context variables"""
    LoggerContext.clear_context(key)
    
    
# Example usage with asyncio.run
async def main():
    logger = get_logger("example", log_level="DEBUG", use_colors=True)
    logger.set_context(txId="req-12345")
    logger.info("Starting async logging example")
    await asyncio.sleep(0.1)
    logger.debug("This is a debug message")
    logger.error("An error occurred")
    logger.log_structured("INFO", {"event": "structured_log", "status": "ok"})
    logger.clear_context(key="request_id")
    logger.info("User context cleared")
    logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())