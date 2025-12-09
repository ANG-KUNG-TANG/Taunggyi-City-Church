import logging
from typing import Dict, Any, Set

class SafeLogger:
    
    REVERSED_ATTRS: Set[str] = {
        'args', 'asctime', 'created','exc_info','exc_text','filename',
        'funcName','levelname','levelno','lineno','module','msecs',
        'message','msg','name','pathname','process','processName',
        'relativeCreated','stack_info','thread','threadName','taskName'
    }
    
    @classmethod
    def safe_extra(cls,data: Dict[str, Any])-> Dict[str, Any]:
        safe_data={}
        for key, value in data.items():
            safet_key= cls._make_key_safe(key)
            safe_data[safet_key] = value
        return safe_data
    
    @classmethod
    def _make_key_safe(cls,key:str)-> str:
        if key in cls.REVERSED_ATTRS:
            return f'_{key}'
        return key
    
    @classmethod
    def log(cls, logger: logging.Logger, level:int, message: str, **kwargs):
        if 'extra' in kwargs:
            kwargs['extra'] = cls.safe_extra(kwargs['extra'])
            logger.log(level, message, **kwargs)
            
    @classmethod
    def debug(cls, logger: logging.Logger, message: str, **kwargs):
        cls.log(logger, logging.DEBUG, message, **kwargs)
        
    @classmethod
    def info(cls, logger: logging.Logger, message:str, **kwargs):
        cls.log(logger, logging.INFO, message, **kwargs)
    
    @classmethod
    def warning(cls, logger: logging.Logger, message:str, **kwargs):
        cls.log(logger, logging.WARNING, message, **kwargs)
    
    @classmethod
    def error(cls, logger: logging.Logger, message:str, **kwargs):
        cls.log(logger, logging.ERROR, message, **kwargs)

    @classmethod
    def critical(cls, logger: logging.Logger, message:str, **kwargs):
        cls.log(logger, logging.CRITICAL, message, **kwargs)
        