import datetime
from typing import Callable, Any, Dict, Optional
import logging
from functools import wraps
from django.db import DatabaseError, IntegrityError, OperationalError

from helpers.exceptions.domain.base_exception import BaseApplicationException
from helpers.exceptions.domain.domain_exceptions import (
    AuthenticationException, PermissionException, ObjectNotFoundException,
    DatabaseConnectionException, DatabaseTimeoutException, MySQLIntegrityException
)
from helpers.exceptions.domain.http_exceptions import ExternalServiceException
from helpers.exceptions.domain.error_codes import ErrorCode
from helpers.exceptions.db.db_mapper import db_exception_mapper
from .loggers import default_logger
from .error_monitor import ErrorEvent, ErrorMonitor, AlertManager

error_monitor = ErrorMonitor()
alert_manager = AlertManager({})

class ErrorHandler:
    def __init__(self, logger: logging.Logger = default_logger.logger, config: Dict[str, Any] = {}):
        self.logger = logger
        self.config = config
        self._exception_handlers: Dict[type, Callable] = {}
        self._register_default_handlers()
        error_monitor.subscribe(alert_manager.evaluate_alert)

    def _register_default_handlers(self) -> None:
        self._exception_handlers.update({
            DatabaseConnectionException: self._handle_database_connection_exception,
            DatabaseTimeoutException: self._handle_database_timeout_exception,
            MySQLIntegrityException: self._handle_database_integrity_exception,
            BaseApplicationException: self._handle_application_exception,
            AuthenticationException: self._handle_auth_exception,
            PermissionException: self._handle_permission_exception,
            ObjectNotFoundException: self._handle_resource_exception,
            ExternalServiceException: self._handle_external_service_exception,
            DatabaseError: self._handle_django_database_error,
            IntegrityError: self._handle_django_database_error,
            OperationalError: self._handle_django_database_error,
            Exception: self._handle_generic_exception
        })

    def handle(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        if isinstance(exception, (DatabaseError, IntegrityError, OperationalError)):
            exception = db_exception_mapper.map_django_exception(exception, context)
        handler = self._find_handler(type(exception))
        result = handler(exception, context)
        self._log_exception(exception, context, result)
        error_monitor.notify(ErrorEvent(exception, context, datetime.datetime.utcnow(), "HIGH"))
        return result

    def _find_handler(self, exception_type: type) -> Callable:
        for exc_type in exception_type.__mro__:
            if exc_type in self._exception_handlers:
                return self._exception_handlers[exc_type]
        return self._exception_handlers[Exception]

    def _handle_database_connection_exception(self, exc: DatabaseConnectionException, context: dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": "Database connection failed",
                "type": "DATABASE_CONNECTION_ERROR"
            },
            "status_code": exc.status_code
        }

    def _handle_database_timeout_exception(self, exc: DatabaseTimeoutException, context: dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": "Database operation timed out",
                "type": "DATABASE_TIMEOUT"
            },
            "status_code": exc.status_code
        }

    def _handle_database_integrity_exception(self, exc: MySQLIntegrityException, context: dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": "Data integrity violation",
                "type": "DATA_INTEGRITY_ERROR"
            },
            "status_code": exc.status_code
        }

    def _handle_application_exception(self, exc: BaseApplicationException, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "APPLICATION_ERROR"
            },
            "status_code": exc.status_code
        }

    def _handle_auth_exception(self, exc: AuthenticationException, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "AUTHENTICATION_ERROR"
            },
            "status_code": exc.status_code
        }

    def _handle_permission_exception(self, exc: PermissionException, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "PERMISSION_ERROR"
            },
            "status_code": exc.status_code
        }

    def _handle_resource_exception(self, exc: ObjectNotFoundException, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "RESOURCE_NOT_FOUND"
            },
            "status_code": exc.status_code
        }

    def _handle_external_service_exception(self, exc: ExternalServiceException, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": "Service temporarily unavailable",
                "type": "SERVICE_UNAVAILABLE"
            },
            "status_code": exc.status_code
        }

    def _handle_django_database_error(self, exc: Exception, context: Dict) -> Dict[str, Any]:
        mapped_exc = db_exception_mapper.map_django_exception(exc, context)
        return self.handle(mapped_exc, context)

    def _handle_generic_exception(self, exc: Exception, context: Dict) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": ErrorCode.UNKNOWN.value,
                "message": "An internal error occurred",
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
        if isinstance(exception, BaseApplicationException):
            log_data.update(exception.context)
        category = 'database' if isinstance(exception, (DatabaseError, IntegrityError, OperationalError)) else 'server' if result["status_code"] >= 500 else 'client'
        log_data['error_category'] = category
        if category == 'server':
            self.logger.error("Server error occurred", extra=log_data)
        else:
            self.logger.warning("Client error occurred", extra=log_data)