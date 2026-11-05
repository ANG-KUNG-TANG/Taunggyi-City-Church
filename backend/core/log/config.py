import logging
import logging.config
import os
import json
from typing import Dict, Any, Optional
from pythonjsonlogger import jsonlogger


def setup_logging(
    default_level: str = "INFO",
    log_format: str = "json",  # "json" or "text"
    log_file: Optional[str] = None,
    enable_console: bool = True
):
    """
    Setup centralized logging configuration.
    
    Args:
        default_level: Default log level
        log_format: Log format (json/text)
        log_file: Optional log file path
        enable_console: Enable console logging
    """
    log_level = getattr(logging, default_level.upper(), logging.INFO)
    
    # Configure handlers
    handlers = {}
    
    if enable_console:
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed' if log_format == 'text' else 'json',
            'level': log_level,
        }
    
    if log_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed' if log_format == 'text' else 'json',
            'level': log_level,
        }
    
    # Formatters
    text_formatter = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]',
        'datefmt': '%Y-%m-%d %H:%M:%S'
    }
    
    json_formatter = {
        '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d',
        'datefmt': '%Y-%m-%d %H:%M:%S'
    }
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': text_formatter,
            'json': json_formatter,
        },
        'handlers': handlers,
        'loggers': {
            '': {  # Root logger
                'handlers': list(handlers.keys()),
                'level': log_level,
                'propagate': True,
            },
            'apps': {
                'handlers': list(handlers.keys()),
                'level': log_level,
                'propagate': False,
            },
        }
    }
    
    logging.config.dictConfig(config)
    
    # Set specific loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with standardized naming."""
    # Ensure module-style naming
    if not name.startswith('apps.'):
        name = f'apps.{name}'
    
    return logging.getLogger(name)