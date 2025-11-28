from typing import Dict, Any
from rest_framework.request import Request

def build_context(request: Request) -> Dict[str, Any]:
    """Build context dictionary from request"""
    context = {
        "request": request,
        "user": request.user if hasattr(request, 'user') else None
    }
    
    # Add IP and user agent for audit logging
    if hasattr(request, 'META'):
        context.update({
            "ip_address": get_client_ip(request),
            "user_agent": request.META.get('HTTP_USER_AGENT', '')
        })
    
    return context

def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip

def get_pagination_params(request: Request) -> tuple[int, int]:
    """Extract pagination parameters from request"""
    try:
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        
        # Validate bounds
        page = max(1, page)
        per_page = max(1, min(per_page, 100))  # Cap at 100 items per page
        
        return page, per_page
    except (TypeError, ValueError):
        return 1, 20

def extract_filters(request: Request) -> Dict[str, Any]:
    """Extract filter parameters from request"""
    filters = {}
    exclude_params = ['page', 'per_page', 'search', 'format', 'ordering']
    
    for key, value in request.query_params.items():
        if key not in exclude_params and value not in ['', None]:
            # Handle boolean values
            if value.lower() in ['true', 'false']:
                filters[key] = value.lower() == 'true'
            else:
                filters[key] = value
    
    return filters