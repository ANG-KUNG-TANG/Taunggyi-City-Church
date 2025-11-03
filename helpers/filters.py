import logging
from threading import local

_thread_local = local()

class RequestIdFilter(logging.Filter):
    """
    Injects request_id from thread-local storage into log records
    """
    def filter(self, record):
        request_id = getattr(_thread_local, 'request_id', 'no-request-id')
        record.request_id = request_id
        return True

def set_request_id(request_id: str):
    """Set request_id for current thread/request"""
    _thread_local.request_id = request_id

def get_request_id() -> str:
    return getattr(_thread_local, 'request_id', 'no-request-id')

def clear_request_id():
    """Clear request_id after request"""
    if hasattr(_thread_local, 'request_id'):
        del _thread_local.request_id