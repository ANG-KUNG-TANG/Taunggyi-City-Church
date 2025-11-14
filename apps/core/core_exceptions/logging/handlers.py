import logging
import asyncio
import smtplib
from typing import Any, Dict, List, Optional
from logging import Handler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AsyncLogHandler(Handler):
    """
    Asynchronous log handler for non-blocking logging.
    Processes log records in background to avoid blocking the main thread.
    """
    
    def __init__(self, level: int = logging.NOTSET, max_queue_size: int = 1000):
        super().__init__(level)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task = None
        self._is_running = False
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record asynchronously.
        
        Args:
            record: Log record to emit
        """
        if not self._is_running:
            return
        
        try:
            # Put the record in the queue for async processing
            asyncio.create_task(self._queue.put(record))
        except Exception as e:
            # If async processing fails, fall back to sync logging
            self.handleError(record)
    
    async def _process_record(self, record: logging.LogRecord) -> None:
        """
        Process a log record asynchronously.
        
        Args:
            record: Log record to process
        """
        try:
            # This is where you'd send logs to external services
            # For now, we'll just format and use a fallback handler
            msg = self.format(record)
            
            # Use a fallback console handler for critical errors
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
    Sends critical errors to external monitoring systems.
    """
    
    def __init__(self, level: int = logging.ERROR):
        super().__init__(level)
        self._monitoring_enabled = False
        self._setup_monitoring()
    
    def _setup_monitoring(self) -> None:
        """Setup error monitoring integration."""
        try:
            # Check if Sentry is configured
            import sentry_sdk
            if sentry_sdk.Hub.current.client:
                self._monitoring_enabled = True
                return
        except ImportError:
            pass
        
        # Check for other monitoring services
        # Add integration with DataDog, New Relic, etc.
        
        self._monitoring_enabled = False
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit log record to error monitoring service.
        
        Args:
            record: Log record to emit
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
        
        Args:
            record: Log record to send
        """
        extra_data = {}
        
        # Extract extra fields
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
            if record.exc_info:
                sentry_sdk.capture_exception(
                    record.exc_info[1],
                    extra=extra_data
                )
            else:
                sentry_sdk.capture_message(
                    record.getMessage(),
                    level=record.levelname.lower(),
                    extra=extra_data
                )
        except ImportError:
            # Sentry not available
            pass


class EmailAlertHandler(Handler):
    """
    Email alert handler for critical errors.
    Sends email notifications for critical application errors.
    """
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        subject_prefix: str = "[CMS Alert]",
        level: int = logging.ERROR
    ):
        super().__init__(level)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.subject_prefix = subject_prefix
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Send email alert for critical errors.
        
        Args:
            record: Log record to send as alert
        """
        try:
            self._send_email_alert(record)
        except Exception:
            self.handleError(record)
    
    def _send_email_alert(self, record: logging.LogRecord) -> None:
        """
        Send email alert.
        
        Args:
            record: Log record to send
        """
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        msg['Subject'] = f"{self.subject_prefix} {record.levelname}: {record.getMessage()}"
        
        # Create email body
        body = f"""
Critical Error Alert

Time: {record.asctime}
Level: {record.levelname}
Logger: {record.name}
Location: {record.pathname}:{record.lineno}
Message: {record.getMessage()}

Exception:
{self.format(record)}

Additional Context:
{getattr(record, 'request_id', 'N/A')}
{getattr(record, 'user_id', 'N/A')}
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)