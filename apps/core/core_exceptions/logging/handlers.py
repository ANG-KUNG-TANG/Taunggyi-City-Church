import logging
import asyncio
from typing import Any
from logging import Handler


class AsyncLogHandler(Handler):
    """
    Asynchronous log handler for non-blocking logging.
    """
    
    def __init__(self, level: int = logging.NOTSET, max_queue_size: int = 1000):
        super().__init__(level)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task = None
        self._is_running = False
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record asynchronously.
        """
        if not self._is_running:
            return
        
        try:
            asyncio.create_task(self._queue.put(record))
        except Exception:
            self.handleError(record)
    
    async def _process_record(self, record: logging.LogRecord) -> None:
        """
        Process a log record asynchronously.
        """
        try:
            msg = self.format(record)
            
            # Use fallback for critical errors
            if record.levelno >= logging.ERROR:
                fallback_handler = logging.StreamHandler()
                fallback_handler.setFormatter(self.formatter)
                fallback_handler.emit(record)
            
        except Exception:
            self.handleError(record)
    
    async def start(self) -> None:
        """Start the async log processor."""
        if self._is_running:
            return
        
        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker())
    
    async def stop(self) -> None:
        """Stop the async log processor."""
        self._is_running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def _worker(self) -> None:
        """Worker coroutine to process log records."""
        while self._is_running:
            try:
                record = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_record(record)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue


class ErrorMonitoringHandler(Handler):
    """
    Log handler for error monitoring services (Sentry, DataDog, etc.).
    Integrated Sentry functionality from removed sentry.py.
    """
    
    def __init__(self, level: int = logging.ERROR):
        super().__init__(level)
        self._monitoring_enabled = False
        self._setup_monitoring()
    
    def _setup_monitoring(self) -> None:
        """Setup error monitoring integration."""
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            
            # Check if Sentry is configured
            dsn = getattr(sentry_sdk.Hub.current.client, 'dsn', None)
            if dsn:
                self._monitoring_enabled = True
                
                # Configure Sentry logging integration
                sentry_logging = LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR  # Send errors as events
                )
                
                # Re-init with logging integration if not already done
                if not any(isinstance(i, LoggingIntegration) for i in sentry_sdk.Hub.current.client.integrations):
                    sentry_sdk.init(
                        dsn=dsn,
                        integrations=[sentry_logging],
                        before_send=self._before_send,
                        before_breadcrumb=self._before_breadcrumb,
                    )
                    
        except ImportError:
            # Sentry not available
            pass
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit log record to error monitoring service.
        """
        if not self._monitoring_enabled or record.levelno < self.level:
            return
        
        try:
            self._send_to_monitoring(record)
        except Exception:
            self.handleError(record)
    
    def _send_to_monitoring(self, record: logging.LogRecord) -> None:
        """
        Send log record to error monitoring service.
        """
        extra_data = {}
        
        # Extract context and extra fields
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            ]:
                extra_data[key] = value
        
        # Send to Sentry
        try:
            import sentry_sdk
            
            # Set context
            with sentry_sdk.configure_scope() as scope:
                for key, value in extra_data.items():
                    scope.set_extra(key, value)
            
            if record.exc_info:
                sentry_sdk.capture_exception(record.exc_info[1])
            else:
                sentry_sdk.capture_message(
                    record.getMessage(),
                    level=record.levelname.lower()
                )
                
        except ImportError:
            # Sentry not available
            pass
    
    def _before_send(self, event, hint):
        """Filter or modify events before sending to Sentry."""
        # Filter out specific exceptions if needed
        exception = hint.get('exc_info')
        if exception:
            # Don't send specific exception types
            pass
        
        # Add custom tags
        event.setdefault('tags', {}).update({
            'handler': 'ErrorMonitoringHandler'
        })
        
        return event
    
    def _before_breadcrumb(self, crumb, hint):
        """Filter or modify breadcrumbs before adding them."""
        # Filter out noisy breadcrumbs
        if crumb.get('category') in ['http', 'console']:
            return None
        
        return crumb