from typing import Dict, Any, Tuple
from rest_framework.request import Request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def build_context(request: Request) -> Dict[str, Any]:
    """
    Build comprehensive context for controller layer
    """
    context = {
        "request": request,
        "user": getattr(request, 'user', None),
        "request_meta": _extract_request_meta(request),
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user else None
    }
    
    # Add request ID if available from middleware
    if hasattr(request, 'request_id'):
        context['request_id'] = request.request_id
        
    return context

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

def get_pagination_params(request: Request) -> Tuple[int, int]:
    """
    Extract and validate pagination parameters from the request.
    Returns: (page, per_page)
    """
    try:
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        
        # Ensure positive numbers
        page = max(1, page)
        per_page = max(1, per_page)
        
        # Cap per_page to avoid too large numbers
        if per_page > 100:
            per_page = 100
            
        return page, per_page
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Invalid pagination parameters: {e}")
        return 1, 20  # Return defaults on error

def extract_filters(request: Request) -> Dict[str, Any]:
    """
    Extract filter parameters from the request query parameters.
    Excludes pagination parameters and common reserved parameters.
    """
    filters = {}
    reserved_params = {'page', 'per_page', 'search', 'sort', 'order', 'format'}
    
    for key, value in request.query_params.items():
        if key not in reserved_params and value not in ['', None]:
            # Handle multiple values for the same parameter
            if key in filters:
                if isinstance(filters[key], list):
                    filters[key].append(value)
                else:
                    filters[key] = [filters[key], value]
            else:
                filters[key] = value
            
    return filters