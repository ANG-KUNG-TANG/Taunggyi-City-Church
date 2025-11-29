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
        
        # Add custom attributes (including context)
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
        """
        # Ensure context fields are present with defaults
        if not hasattr(record, 'request_id'):
            record.request_id = 'N/A'
        
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
        
        if context_parts:
            formatted += f" [{', '.join(context_parts)}]"
        
        # Add exception information if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted