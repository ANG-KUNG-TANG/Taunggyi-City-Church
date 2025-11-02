import datetime
from typing import Callable, Any, Dict
import logging
from functools import wraps

from helpers.excepitons.base_exception import BaseApplicaitonException, ValdationException
from helpers.excepitons.domain_exceptons import AuthenticationException, ExternalServiceException, ResourceNotFoundException


class ErrorHandler:
    def __init__(self, logger: logging, config: Dict[str, Any]):
        self.logger = logger
        self.config = config
        self._exception_handlers: Dict[type, Callable] = {}
        self._register_default_handlers()
        
    def _register_defaut_handlers(self) -> None:
        
        self._exception_handlers.update(
            {
                ValdationException: self._handle_validation_exception,
                AuthenticationException: self._handler_auth_exception,
                AuthenticationException: self._handle_auth_exception,
                ResourceNotFoundException: self._handle_resouce_exception,
                ExternalServiceException: self._handle_external_service_exception,
                Exception: self._handle_generic_exception
            }
        )
    
    def handle(self, exception: Exception, contex: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        
        handler = self._find_handler(type(exception))
        result = handler(exception, context)
        
        self._log_exception(exception, context, result)
        return result
    
    def _find_handler(self, exception_type:type)-> Callable:
        for exc_type in exception_type.__mro__:
            if exc_type in self._exception_handlers:
                 return self._exception_handlers[exc_type]
        return self._exception_handlers[Exception]
    
    def _handle_validation_exception(self, exc: ValdationException, contex: dict)->Dict[str,Any]:
        return{
            'success': False,
            'error': {
                'code': exc.error_code,
                'message': exc.message,
                'details': exc.details,
                'type': "VALIDATION_ERROR"
            },
            "status_code": exc.status_code
        }
        
    def _handler_external_service_exception(self, exc: ExternalServiceException, context: Dict) -> Dict[str, Any]:
        return{
            "success": False,
            "error": {
                "code" : exc.error_code,
                "message": "Service temporarily unavilable",
                "type": "SERVICE_UNAVAILABLE"
            },
            "status_code": exc.status_code
        }
    
    def _handle_generic_excepton(self, exc: Exception, context: Dict) -> Dict[str, Any]:
        return{
            "success": False,
            "error": {
                "code" : "INTERNAL_ERROR",
                "message": "An internal error occured",
                "type": "INTERNAL_ERROR"
            },
            "status_code": 500
        }
    
    def _log_exception(self, exception: Exception, context: Dict, result: Dict) -> None:
        log_data = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "error_code": getattr(exception, "error_code", "UNKNOWN"),
            "status_code": result.get("status_code", 500),
            "context": context,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        if isinstance(exception, BaseApplicaitonException):
            log_data.update(exception.context)
        self.logger.error("Excepiton handled", extra=log_data)
        
    def register_handler(self, exception_type: type, handler: Callable) -> None:
        self._exception_handlers[exception_type] = handler
        
    def wrap_async(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = self._build_context(func, args, kwargs)
                result = self.handle(e.context)
                if result['status_code'] >= 500:
                    raise "Unexpected error occured"
                return result
        return async_wrapper
    
    def wrap_sync(self, func: callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = self._build_context(func, args, kwargs)
                result = self.handle(e, context)
                if result['status_code'] >= 500:
                    raise "Unexpected error occured"
                return result
        return sync_wrapper
    
    def _build_context(self, func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        return{
            'function': f'{func.__module__}.{func.__name__}',
            'args': str(args),
            "kwargs": str(kwargs),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        