from typing import Dict, Any
from rest_framework.request import Request
from datetime import datetime

def build_context(request: Request) -> Dict[str, Any]:
    """
    Build minimal context for controller layer
    """
    return {
        "request_meta": _extract_request_meta(request),
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None
    }

def _extract_request_meta(request: Request) -> Dict[str, Any]:
    """
    Extract request metadata for audit logging
    """
    if not hasattr(request, 'META'):
        return {}
    
    return {
        "ip_address": _get_client_ip(request),
        "user_agent": request.META.get('HTTP_USER_AGENT', ''),
        "http_method": request.method,
        "path_info": request.META.get('PATH_INFO', '')
    }

def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        return ips[0]
    return request.META.get('REMOTE_ADDR', 'unknown')