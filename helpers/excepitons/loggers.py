from asyncio import Event
import datetime
import logging
import logging.config
import json
from pathlib import Path
from typing import Dict, Any

from apps.tcc.models import users



class StructureFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord)->str:
        log_data = {
            "timesatamp": self.formatTime(record),
            "level": record.levelname,
            "logger" : record.name,
            "message" : record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)
    
def setup_logging(config: Dict[str, Any]) -> None:
    
    log_config = {
        "version": 1,
        "disable_existing_loggers" : False,
        "formatters": {
            "structured":{
                "()": StructureFormatter,
            },
            'detailed': {
                "format": "%(asctime)s - %(name)s - %(levelname)s -%(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": config.get('console_level', "INFO"),
                "formatter": "Structured",
                "stream": "ext://sys.stdout"
            },
            "file":{
                "class": "logging.handles.Rotatingfilehandler",
                "level": config.get('file_level', "INFO"),
                "formatter": "structured",
                "filename": config.get("log_file", "app.log"),
                "maxBytes": 1048760,
                "backupCount": 5
            }
        },
        "loggers":{
            "app":{
                "level": config.get("root_levle", "INFO"),
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "security": {
                'level': "INFO",
                'handlers': ["console", "file"],
                "propagate": False
            }
        },
        "roto": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
    logging.config.dictConfig(log_config)
    
class ContextLogger:
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
        
    def bind(self, **kwargs)-> "ContextLogger":
        self.context.update(kwargs)
        return self
    def clear_context(self) -> None:
        self.context.clear()
        
    def _log_with_context(self, level: int, msg: str, extra: Dict[str, Any] = None):
        extra_data = self.context.copy()
        if extra:
            extra_data.update(extra)
        
        if extra_data:
            self.logger.log(level, msg, extra={'extra_data': extra_data})
        else:
            self.logger.log(level, msg)
    
    def info(self, msg: str, extra: Dict[str, Any] = None):
        self._log_with_context(logging.INFO, msg, extra)
        
    def error(self, msg: str, extra: Dict[str, Any] = None):
        self._log_with_context(logging.ERROR, msg, extra)
        
    def warning(self, msg:str, extra: Dict[str,Any] = None):
        self._log_with_context(logging.WARNING, msg, extra)
        
    def debug(self, msg: str, extra: Dict[str, Any] = None):
        self._log_with_context(logging.DEBUG, msg, extra)
        
    def audit(self, msg: str, user: str, details: Dict[str, Any]=None):
        audit_data = {
            "event_type": "audit",
            "event": Event,
            "user": users,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        if details:
            audit_data.update(details)
        self.info(f'Audit event: {Event}', extra=audit_data)
       