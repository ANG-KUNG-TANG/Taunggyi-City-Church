"""
Base View Utilities - Standard DRF
Common functions for building context, pagination, and filtering
"""
from typing import Dict, Any, Tuple, Optional
from rest_framework.request import Request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================
# CONTEXT BUILDING
# ============================================

def build_context(request: Request) -> Dict[str, Any]:
    """
    Build comprehensive context for controller layer
    
    Args:
        request: DRF Request object
        
    Returns:
        Dict containing request metadata, user info, and timestamps
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
    
    # Add session ID if available
    if hasattr(request, 'session') and request.session.session_key:
        context['session_id'] = request.session.session_key
        
    return context


def _extract_request_meta(request: Request) -> Dict[str, Any]:
    """
    Extract request metadata for audit logging
    
    Args:
        request: DRF Request object
        
    Returns:
        Dict containing IP, user agent, method, and path
    """
    if not hasattr(request, 'META'):
        return {}
    
    return {
        "ip_address": _get_client_ip(request),
        "user_agent": request.META.get('HTTP_USER_AGENT', ''),
        "http_method": request.method,
        "path_info": request.META.get('PATH_INFO', ''),
        "content_type": request.META.get('CONTENT_TYPE', ''),
        "referer": request.META.get('HTTP_REFERER', ''),
    }


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, considering proxies
    
    Args:
        request: DRF Request object
        
    Returns:
        Client IP address as string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get first IP in the chain (client IP)
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        return ips[0]
    return request.META.get('REMOTE_ADDR', 'unknown')


# ============================================
# PAGINATION UTILITIES
# ============================================

def get_pagination_params(request: Request, default_page: int = 1, default_per_page: int = 20) -> Tuple[int, int]:
    """
    Extract and validate pagination parameters from the request.
    
    Args:
        request: DRF Request object
        default_page: Default page number if not provided
        default_per_page: Default items per page if not provided
        
    Returns:
        Tuple of (page, per_page)
    """
    try:
        page = int(request.query_params.get('page', default_page))
        per_page = int(request.query_params.get('per_page', default_per_page))
        
        # Ensure positive numbers
        page = max(1, page)
        per_page = max(1, per_page)
        
        # Cap per_page to avoid too large numbers
        max_per_page = 100
        if per_page > max_per_page:
            logger.warning(f"per_page {per_page} exceeds maximum {max_per_page}, capping to {max_per_page}")
            per_page = max_per_page
            
        return page, per_page
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Invalid pagination parameters: {e}, using defaults")
        return default_page, default_per_page


def build_pagination_response(
    items: list,
    total_count: int,
    page: int,
    per_page: int,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build standardized pagination response
    
    Args:
        items: List of items for current page
        total_count: Total number of items across all pages
        page: Current page number
        per_page: Items per page
        additional_data: Optional additional data to include in response
        
    Returns:
        Dict with items and pagination metadata
    """
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    
    response = {
        'items': items,
        'pagination': {
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    }
    
    if additional_data:
        response.update(additional_data)
    
    return response


# ============================================
# FILTERING UTILITIES
# ============================================

def extract_filters(request: Request, excluded_params: Optional[set] = None) -> Dict[str, Any]:
    """
    Extract filter parameters from the request query parameters.
    Excludes pagination parameters and common reserved parameters.
    
    Args:
        request: DRF Request object
        excluded_params: Additional parameters to exclude
        
    Returns:
        Dict of filter parameters
    """
    # Default reserved params
    reserved_params = {'page', 'per_page', 'search', 'sort', 'order', 'format', 'limit', 'offset'}
    
    # Add any additional excluded params
    if excluded_params:
        reserved_params.update(excluded_params)
    
    filters = {}
    
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


def extract_sort_params(request: Request, default_sort: str = 'created_at', default_order: str = 'desc') -> Tuple[str, str]:
    """
    Extract sorting parameters from request
    
    Args:
        request: DRF Request object
        default_sort: Default field to sort by
        default_order: Default sort order ('asc' or 'desc')
        
    Returns:
        Tuple of (sort_by, sort_order)
    """
    sort_by = request.query_params.get('sort_by', default_sort)
    sort_order = request.query_params.get('sort_order', default_order).lower()
    
    # Validate sort order
    if sort_order not in ['asc', 'desc']:
        logger.warning(f"Invalid sort_order '{sort_order}', using '{default_order}'")
        sort_order = default_order
    
    return sort_by, sort_order


def extract_search_query(request: Request) -> Optional[str]:
    """
    Extract search query from request
    
    Args:
        request: DRF Request object
        
    Returns:
        Search query string or None
    """
    # Check common search parameter names
    search_params = ['q', 'query', 'search']
    
    for param in search_params:
        query = request.query_params.get(param)
        if query:
            return query.strip()
    
    return None


# ============================================
# VALIDATION UTILITIES
# ============================================

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Tuple[bool, Optional[str]]:
    """
    Validate that required fields are present in data
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def sanitize_dict(data: Dict[str, Any], remove_fields: Optional[list] = None) -> Dict[str, Any]:
    """
    Sanitize dictionary by removing sensitive or unwanted fields
    
    Args:
        data: Dictionary to sanitize
        remove_fields: List of field names to remove
        
    Returns:
        Sanitized dictionary
    """
    if not remove_fields:
        remove_fields = ['password', 'password_hash', 'salt', 'tokens', 'secret']
    
    sanitized = data.copy()
    
    for field in remove_fields:
        sanitized.pop(field, None)
    
    return sanitized


# ============================================
# USER UTILITIES
# ============================================

def get_current_user_id(request: Request) -> Optional[int]:
    """
    Safely extract current user ID from request
    
    Args:
        request: DRF Request object
        
    Returns:
        User ID or None if not authenticated
    """
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return getattr(request.user, 'id', None)
    return None


def is_admin_user(request: Request) -> bool:
    """
    Check if current user is an admin
    
    Args:
        request: DRF Request object
        
    Returns:
        True if user is admin, False otherwise
    """
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False)
    return False


# ============================================
# RESPONSE UTILITIES
# ============================================

def build_error_response(message: str, error_code: str = 'ERROR', status_code: int = 400) -> Dict[str, Any]:
    """
    Build standardized error response
    
    Args:
        message: Error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        
    Returns:
        Error response dictionary
    """
    return {
        'success': False,
        'message': message,
        'error_code': error_code,
        'status_code': status_code
    }


def build_success_response(data: Any, message: str = 'Success') -> Dict[str, Any]:
    """
    Build standardized success response
    
    Args:
        data: Response data
        message: Success message
        
    Returns:
        Success response dictionary
    """
    return {
        'success': True,
        'message': message,
        'data': data
    }


# ============================================
# DATE/TIME UTILITIES
# ============================================

def convert_datetime_fields(data: Dict[str, Any], date_fields: Optional[list] = None) -> Dict[str, Any]:
    """
    Convert datetime objects to ISO format strings
    
    Args:
        data: Dictionary containing datetime fields
        date_fields: List of field names that contain datetime objects
        
    Returns:
        Dictionary with datetime fields converted to strings
    """
    if not date_fields:
        date_fields = ['created_at', 'updated_at', 'last_login', 'date_of_birth', 'expires_at']
    
    result = data.copy()
    
    for field in date_fields:
        if field in result and result[field]:
            value = result[field]
            if hasattr(value, 'isoformat'):
                result[field] = value.isoformat()
    
    return result