import datetime
import logging
import logging.config
import json
from pathlib import Path
from typing import Dict, Any
from config.middleware import RequestIDFilter


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, 'request_id', 'no-request-id'),
        }
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)

def setup_logging(config: Dict[str, Any]) -> None:
    log_dir = Path(config.get('log_dir', 'logs'))
    log_dir.mkdir(exist_ok=True)

    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'request_id': {
                '()': RequestIDFilter,
            },
        },
        'formatters': {
            'structured': {
                '()': StructuredFormatter,
                'format': '{ "timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
                          '"message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", '
                          '"line": %(lineno)d, "request_id": "%(request_id)s" }'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': config.get('console_level', 'INFO'),
                'formatter': 'structured',
                'filters': ['request_id'],
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': config.get('file_level', 'INFO'),
                'formatter': 'structured',
                'filename': log_dir / 'app.log',
                'maxBytes': 10485760,
                'backupCount': 5,
                'filters': ['request_id'],
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'structured',
                'filename': log_dir / 'errors.log',
                'maxBytes': 10485760,
                'backupCount': 5,
                'filters': ['request_id'],
            },
        },
        'loggers': {
            'app': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False,
            },
            'db': {
                'level': 'INFO',
                'handlers': ['console', 'error_file'],
                'propagate': False,
            },
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console'],
        },
    }

    logging.config.dictConfig(log_config)

class ContextLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}

    def bind(self, **kwargs):
        self.context.update(kwargs)
        return self

    def _log(self, level, msg, extra=None):
        extra_data = self.context.copy()
        if extra:
            extra_data.update(extra)
        self.logger.log(level, msg, extra={'extra_data': extra_data})

    def info(self, msg, extra=None):
        self._log(logging.INFO, msg, extra)

    def error(self, msg, extra=None):
        self._log(logging.ERROR, msg, extra)

# Global logger
default_logger = ContextLogger("app")