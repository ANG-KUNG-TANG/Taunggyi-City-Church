# urls.py - SIMPLIFIED VERSION
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

# ============ DIRECT IMPORTS ============

# Try absolute imports first
try:
    # Import user views directly
    from .views.user_view import (
        health_check_view,
        register_user_view,
        create_admin_user_view,
        get_current_user_profile_view,
        get_user_by_id_view,
        get_all_users_view,
        update_user_view,
        update_current_user_profile_view,
        check_email_availability_view,
        delete_user_view,
    )
    
    # Check if the views are callable
    if not callable(register_user_view):
        raise ImportError("register_user_view is not callable")
        
    logger.info("Successfully imported user views")
    
except ImportError as e:
    logger.error(f"Failed to import user views: {e}")
    # Re-raise to see the actual error
    raise

# Try to import auth views (create if they don't exist)
try:
    from .views.auth_view import (
        login_view,
        logout_view,
        refresh_token_view,
        verify_token_view,
        forgot_password_view,
        reset_password_view,
    )
except ImportError:
    logger.warning("Auth views not found, using DRF SimpleJWT views")
    
    # Create simple placeholder auth views
    @csrf_exempt
    def placeholder_auth_view(request):
        return JsonResponse({
            'error': 'Auth endpoint not configured',
            'message': 'This authentication endpoint requires setup',
            'status': 501
        }, status=501)
    
    # Assign placeholders
    login_view = placeholder_auth_view
    logout_view = placeholder_auth_view
    refresh_token_view = placeholder_auth_view
    verify_token_view = placeholder_auth_view
    forgot_password_view = placeholder_auth_view
    reset_password_view = placeholder_auth_view

# ============ ROOT VIEW ============

@csrf_exempt
def tcc_api_root(request):
    """API root endpoint"""
    return JsonResponse({
        'message': 'TCC API Server is running',
        'version': '1.0.0',
        'status': 'operational',
        'timestamp': request._request_time.isoformat() if hasattr(request, '_request_time') else None,
        'endpoints': {
            'auth': {
                'login': '/tcc/auth/login/',
                'logout': '/tcc/auth/logout/',
                'refresh': '/tcc/auth/refresh/',
                'verify': '/tcc/auth/verify/',
                'forgot_password': '/tcc/auth/forgot-password/',
                'reset_password': '/tcc/auth/reset-password/',
            },
            'users': {
                'register': '/tcc/users/register/',
                'current_profile': '/tcc/users/me/',
                'user_by_id': '/tcc/users/<id>/',
                'list_users': '/tcc/users/all/',
                'check_email': '/tcc/users/check-email/',
                'health': '/tcc/health/',
            }
        }
    })

# ============ URL PATTERNS ============

urlpatterns = [
    # Root endpoint
    path('', tcc_api_root, name='tcc-api-root'),
    
    # Health check
    path('health/', health_check_view, name='health-check'),
    
    # Auth endpoints
    path('auth/login/', login_view, name='auth-login'),
    path('auth/logout/', logout_view, name='auth-logout'),
    path('auth/refresh/', refresh_token_view, name='auth-refresh'),
    path('auth/verify/', verify_token_view, name='auth-verify'),
    path('auth/forgot-password/', forgot_password_view, name='auth-forgot-password'),
    path('auth/reset-password/', reset_password_view, name='auth-reset-password'),
    
    # User endpoints
    path('users/register/', register_user_view, name='user-register'),
    path('users/admin/create/', create_admin_user_view, name='create-admin-user'),
    path('users/me/', get_current_user_profile_view, name='current-user-profile'),
    path('users/me/update/', update_current_user_profile_view, name='update-current-user'),
    path('users/all/', get_all_users_view, name='all-users'),
    path('users/<int:user_id>/', get_user_by_id_view, name='user-by-id'),
    path('users/<int:user_id>/update/', update_user_view, name='update-user'),
    path('users/<int:user_id>/delete/', delete_user_view, name='delete-user'),
    path('users/check-email/', check_email_availability_view, name='check-email'),
]