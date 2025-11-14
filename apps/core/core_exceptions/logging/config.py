import logging
import logging.config
import os
import sys
from typing import Optional, Dict, Any
from enum import Enum

from .filters import ContextFilter
from .formatters import JSONFormatter, DetailedFormatter
from .handlers import AsyncLogHandler, ErrorMonitoringHandler


class LogLevel(Enum):
    """Log level enumeration."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_async: bool = False,
    enable_monitoring: bool = False,
    config_overrides: Optional[Dict[str, Any]] = None
) -> None:
    """
    Setup comprehensive logging configuration for the application.
    
    Args:
        level: Logging level
        log_file: Optional file path for file logging
        json_format: Whether to use JSON formatting
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        enable_async: Whether to enable async logging
        enable_monitoring: Whether to enable error monitoring
        config_overrides: Additional configuration overrides
    """
    log_handlers = {}
    
    if enable_console:
        log_handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": level.value,
            "formatter": "json" if json_format else "detailed",
            "stream": "ext://sys.stdout",
            "filters": ["context_filter"]
        }
    
    if enable_file and log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        log_handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": level.value,
            "formatter": "json" if json_format else "detailed",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
            "filters": ["context_filter"]
        }
    
    if enable_async:
        log_handlers["async"] = {
            "class": "core.exceptions.logging.handlers.AsyncLogHandler",
            "level": level.value,
            "formatter": "json",
            "filters": ["context_filter"]
        }
    
    if enable_monitoring:
        log_handlers["error_monitoring"] = {
            "class": "core.exceptions.logging.handlers.ErrorMonitoringHandler",
            "level": LogLevel.ERROR.value,
            "formatter": "json",
            "filters": ["context_filter"]
        }
    
    # Base logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context_filter": {
                "()": "core.exceptions.logging.filters.ContextFilter",
            }
        },
        "formatters": {
            "detailed": {
                "()": "core.exceptions.logging.formatters.DetailedFormatter",
            },
            "json": {
                "()": "core.exceptions.logging.formatters.JSONFormatter",
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            }
        },
        "handlers": log_handlers,
        "loggers": {
            "": {  # Root logger
                "level": level.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "core": {
                "level": level.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "django": {
                "level": LogLevel.WARNING.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "django.request": {
                "level": LogLevel.ERROR.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "fastapi": {
                "level": LogLevel.WARNING.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "uvicorn": {
                "level": LogLevel.WARNING.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            },
            "sqlalchemy": {
                "level": LogLevel.WARNING.value,
                "handlers": list(log_handlers.keys()),
                "propagate": False
            }
        }
    }
    
    # Apply overrides
    if config_overrides:
        _deep_update(logging_config, config_overrides)
    
    # Configure logging
    logging.config.dictConfig(logging_config)
    
    # Set up asyncio logging if enabled
    if enable_async:
        logging.getLogger('asyncio').setLevel(LogLevel.WARNING.value)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def _deep_update(original: Dict[str, Any], update: Dict[str, Any]) -> None:
    """
    Recursively update a dictionary.
    
    Args:
        original: Original dictionary to update
        update: Dictionary with updates
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in original and isinstance(original[key], dict):
            _deep_update(original[key], value)
        else:
            original[key] = value


class LoggingContext:
    """
    Context manager for temporary logging configuration.
    """
    
    def __init__(self, level: LogLevel = None, handler=None):
        self.level = level
        self.handler = handler
        self.original_level = None
    
    def __enter__(self):
        if self.level:
            self.original_level = logging.getLogger().level
            logging.getLogger().setLevel(self.level.value)
        
        if self.handler:
            logging.getLogger().addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_level:
            logging.getLogger().setLevel(self.original_level)
        
        if self.handler:
            logging.getLogger().removeHandler(self.handler)