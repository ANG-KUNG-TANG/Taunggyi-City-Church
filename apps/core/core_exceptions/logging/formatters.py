import logging
import json
from datetime import datetime
from typing import Any, Dict
import traceback


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Produces JSON logs for easy parsing and analysis.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._include_traceback = kwargs.get('include_traceback', True)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string representation of log record
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info and self._include_traceback:
            log_entry["exception"] = self.formatException(record.exc_info)
            log_entry["stack_trace"] = traceback.format_exc()
        
        # Add custom attributes
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            ] and not key.startswith('_'):
                # Handle non-serializable objects
                try:
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class DetailedFormatter(logging.Formatter):
    """
    Detailed text formatter for human-readable logs.
    Provides comprehensive log information in a readable format.
    """
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with detailed information.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
        """
        # Ensure context fields are present
        if not hasattr(record, 'request_id'):
            record.request_id = 'N/A'
            
        if not hasattr(record, 'exception_id'):
            record.exception_id = 'N/A'
        
        if not hasattr(record, 'user_id'):
            record.user_id = 'N/A'
        
        # Format the base message
        formatted = super().format(record)
        
        # Add context information
        context_parts = []
        if hasattr(record, 'request_id') and record.request_id != 'N/A':
            context_parts.append(f"req:{record.request_id}")
        
        if hasattr(record, 'user_id') and record.user_id != 'N/A':
            context_parts.append(f"user:{record.user_id}")
        
        if hasattr(record, 'exception_id') and record.exception_id != 'N/A':
            context_parts.append(f"ex:{record.exception_id}")
        
        if context_parts:
            formatted += f" [{', '.join(context_parts)}]"
        
        # Add exception information if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output.
    Adds ANSI color codes to log levels for better readability.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            Colored log string
        """
        # Colorize the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname
        
        return super().format(record)