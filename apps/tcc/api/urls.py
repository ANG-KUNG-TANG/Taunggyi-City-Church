"""
URL Configuration - Standard DRF Routing
Clean, organized, and follows Django/DRF best practices
"""
import traceback
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging
from django.views.generic import RedirectView

logger = logging.getLogger(__name__)

# ============================================
# API ROOT ENDPOINT
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    API Root - Provides overview of available endpoints
    """
    base_url = request.build_absolute_uri('/api').rstrip('/')
    
    return Response({
        'message': 'TCC API Server',
        'version': '1.0.0',
        'status': 'operational',
        'documentation': {
            'api_docs': f'{base_url}/docs/',
            'schema': f'{base_url}/schema/',
            'redoc': f'{base_url}/redoc/'
        },
        'authentication': {
            'token_type': 'Bearer Token',
            'endpoints': {
                'obtain_token': f'{base_url}/auth/login/',
                'refresh_token': f'{base_url}/auth/refresh/',
                'verify_token': f'{base_url}/auth/verify/'
            }
        },
        'endpoints': {
            # Authentication
            'authentication': {
                'login': f'{base_url}/auth/login/',
                'logout': f'{base_url}/auth/logout/',
                'refresh': f'{base_url}/auth/refresh/',
                'verify': f'{base_url}/auth/verify/',
                'forgot_password': f'{base_url}/auth/forgot-password/',
                'reset_password': f'{base_url}/auth/reset-password/',
                'change_password': f'{base_url}/auth/change-password/',
                'status': f'{base_url}/auth/status/'
            },
            
            # User Management
            'users': {
                # Public Registration
                'public_register': f'{base_url}/users/register/',
                'public_register_singular': f'{base_url}/user/register/',
                
                # Admin User Creation
                'admin_create': f'{base_url}/users/',
                'admin_create_singular': f'{base_url}/user/',
                
                # Admin User Creation (flexible)
                'admin_create_flexible': f'{base_url}/users/create-by-admin/',
                'admin_create_flexible_singular': f'{base_url}/user/create-by-admin/',
                
                # User Profile & Management
                'profile': f'{base_url}/users/profile/',
                'profile_singular': f'{base_url}/user/profile/',
                'get_by_id': f'{base_url}/users/by-id/?id=',
                'get_by_id_singular': f'{base_url}/user/by-id/?id=',
                'email_check': f'{base_url}/users/check-email/',
                'email_check_singular': f'{base_url}/user/check-email/',
                
                # Individual User Operations (both singular and plural)
                'user_operations': {
                    'list': f'{base_url}/users/',
                    'list_singular': f'{base_url}/user/',
                    'retrieve': f'{base_url}/users/{{id}}/',
                    'retrieve_singular': f'{base_url}/user/{{id}}/',
                    'update': f'{base_url}/users/{{id}}/',
                    'partial_update': f'{base_url}/users/{{id}}/',
                    'delete': f'{base_url}/users/{{id}}/',
                    'change_status': f'{base_url}/users/{{id}}/change_status/'
                },
                
                # Search & Filter Operations
                'search_operations': {
                    'by_email': f'{base_url}/users/by_email/?email=',
                    'by_email_singular': f'{base_url}/user/by_email/?email=',
                    'by_role': f'{base_url}/users/by_role/?role=',
                    'by_role_singular': f'{base_url}/user/by_role/?role=',
                    'search': f'{base_url}/users/search/?q=',
                    'search_singular': f'{base_url}/user/search/?q='
                },
                
                # Bulk Operations
                'bulk_operations': {
                    'bulk_delete': f'{base_url}/users/bulk_delete/',
                    'bulk_delete_singular': f'{base_url}/user/bulk_delete/'
                },
                
                # Alternative Views
                'alternative_list': f'{base_url}/users/list/',
                'alternative_list_singular': f'{base_url}/user/list/'
            },
            
            # System
            'system': {
                'health_check': f'{base_url}/health/',
                'api_root': f'{base_url}/'
            }
        },
        'note': 'API supports both singular (/api/user/) and plural (/api/users/) endpoints for user operations',
        'status_codes': {
            '200': 'Success',
            '201': 'Created',
            '400': 'Bad Request',
            '401': 'Unauthorized',
            '403': 'Forbidden',
            '404': 'Not Found',
            '409': 'Conflict (Duplicate)',
            '500': 'Server Error'
        }
    })


# ============================================
# API VERSIONING
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_version(request):
    """
    API version information
    """
    return Response({
        'api_name': 'TCC API',
        'version': '1.0.0',
        'status': 'stable',
        'release_date': '2024-01-01',
        'changelog': 'https://api.example.com/docs/changelog',
        'support': {
            'email': 'support@example.com',
            'docs': 'https://api.example.com/docs'
        }
    })


# ============================================
# IMPORT VIEWS
# ============================================

# User views
from apps.tcc.api.views.user_view import (
    RegisterView,
    EmailAvailabilityView,
    HealthCheckView,
    ProfileView,
    UserListView,
    GetyByid,
    UserViewSet
)

try:
    print("DEBUG: Trying to import auth views...")  
    from apps.tcc.api.views.auth_view import (
        LoginView,
        LogoutView,
        RefreshTokenView,
        VerifyTokenView,
        ForgotPasswordView,
        ResetPasswordView,
        AuthStatusView,
        ChangePasswordView,
    )
    print("DEBUG: Successfully imported all auth views!")
    auth_views_available = True
except ImportError as e:
    print(f"DEBUG: Import failed with error: {e}")
    print(f"DEBUG: Full traceback:")
    traceback.print_exc()
    logger.warning(f"Auth views not available: {e}")
    auth_views_available = False
    
    # Create placeholder views
    from rest_framework.views import APIView
    from rest_framework import status
    
    class PlaceholderView(APIView):
        permission_classes = [AllowAny]
        
        def get(self, request):
            return Response({
                'error': 'Endpoint not implemented',
                'message': 'This endpoint is not yet available',
                'status': 'under_development'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
        
        def post(self, request):
            return Response({
                'error': 'Endpoint not implemented',
                'message': 'This endpoint is not yet available',
                'status': 'under_development'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    LoginView = PlaceholderView
    LogoutView = PlaceholderView
    RefreshTokenView = PlaceholderView
    VerifyTokenView = PlaceholderView
    ForgotPasswordView = PlaceholderView
    ResetPasswordView = PlaceholderView
    AuthStatusView = PlaceholderView
    ChangePasswordView = PlaceholderView


# ============================================
# URL PATTERNS
# ============================================

# Helper function to create both singular and plural patterns
def create_user_patterns(prefix='users'):
    """Create user URL patterns with given prefix (users/user)"""
    return [
        # List and create
        path(f'{prefix}/', UserViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }), name=f'{prefix}-list-create'),
        
        # Detail operations
        path(f'{prefix}/<int:pk>/', UserViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), name=f'{prefix}-detail'),
        
        # UserViewSet custom actions
        path(f'{prefix}/by_email/', UserViewSet.as_view({'get': 'by_email'}), name=f'{prefix}-by-email'),
        path(f'{prefix}/search/', UserViewSet.as_view({'get': 'search'}), name=f'{prefix}-search'),
        path(f'{prefix}/by_role/', UserViewSet.as_view({'get': 'by_role'}), name=f'{prefix}-by-role'),
        path(f'{prefix}/bulk_delete/', UserViewSet.as_view({'post': 'bulk_delete'}), name=f'{prefix}-bulk-delete'),
        path(f'{prefix}/<int:pk>/change_status/', UserViewSet.as_view({'patch': 'change_status'}), name=f'{prefix}-change-status'),
        
        # Other user endpoints
        path(f'{prefix}/register/', RegisterView.as_view(), name=f'{prefix}-register'),
        path(f'{prefix}/create-by-admin/', RegisterView.as_view(), name=f'{prefix}-create-by-admin'),
        path(f'{prefix}/check-email/', EmailAvailabilityView.as_view(), name=f'{prefix}-check-email'),
        path(f'{prefix}/profile/', ProfileView.as_view(), name=f'{prefix}-profile'),
        path(f'{prefix}/by-id/', GetyByid.as_view(), name=f'{prefix}-by-id'),
        path(f'{prefix}/list/', UserListView.as_view(), name=f'{prefix}-list-alt'),
    ]

urlpatterns = [
    # ========================================
    # ROOT & SYSTEM ENDPOINTS
    # ========================================
    path('', api_root, name='api-root'),
    path('version/', api_version, name='api-version'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # ========================================
    # AUTHENTICATION ENDPOINTS
    # ========================================
    path('auth/', include([
        path('login/', LoginView.as_view(), name='auth-login'),
        path('logout/', LogoutView.as_view(), name='auth-logout'),
        path('refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
        path('verify/', VerifyTokenView.as_view(), name='auth-verify'),
        path('forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
        path('reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
        path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
        path('status/', AuthStatusView.as_view(), name='auth-status'),
    ])),
]

# Add both singular and plural user patterns
urlpatterns += create_user_patterns('users')  # /api/users/ endpoints
urlpatterns += create_user_patterns('user')   # /api/user/ endpoints


# ============================================
# ADDITIONAL PATTERNS (Optional)
# ============================================

# Add these if you need them
additional_patterns = [
    # Redirect from /api to /api/
    path('', RedirectView.as_view(url='/api/', permanent=True)),
]

# Uncomment to add additional patterns
# urlpatterns += additional_patterns


# ============================================
# URL NAMING REFERENCE
# ============================================
"""
URL Name Reference:

Authentication (same for both):
- auth-login           -> POST   /api/auth/login/
- auth-logout          -> POST   /api/auth/logout/
- auth-refresh         -> POST   /api/auth/refresh/
- auth-verify          -> POST   /api/auth/verify/
- auth-forgot-password -> POST   /api/auth/forgot-password/
- auth-reset-password  -> POST   /api/auth/reset-password/
- auth-change-password -> POST   /api/auth/change-password/
- auth-status          -> GET    /api/auth/status/

User Management (PLURAL - /api/users/):
- users-list-create     -> GET/POST /api/users/
- users-detail          -> GET/PUT/PATCH/DELETE /api/users/{id}/
- users-by-email        -> GET    /api/users/by_email/
- users-search          -> GET    /api/users/search/
- users-by-role         -> GET    /api/users/by_role/
- users-bulk-delete     -> POST   /api/users/bulk_delete/
- users-change-status   -> PATCH  /api/users/{id}/change_status/
- users-register        -> POST   /api/users/register/
- users-create-by-admin -> POST   /api/users/create-by-admin/
- users-check-email     -> GET    /api/users/check-email/
- users-profile         -> GET/PUT/PATCH /api/users/profile/
- users-by-id           -> GET    /api/users/by-id/?id=
- users-list-alt        -> GET    /api/users/list/

User Management (SINGULAR - /api/user/):
- user-list-create     -> GET/POST /api/user/
- user-detail          -> GET/PUT/PATCH/DELETE /api/user/{id}/
- user-by-email        -> GET    /api/user/by_email/
- user-search          -> GET    /api/user/search/
- user-by-role         -> GET    /api/user/by_role/
- user-bulk-delete     -> POST   /api/user/bulk_delete/
- user-change-status   -> PATCH  /api/user/{id}/change_status/
- user-register        -> POST   /api/user/register/
- user-create-by-admin -> POST   /api/user/create-by-admin/
- user-check-email     -> GET    /api/user/check-email/
- user-profile         -> GET/PUT/PATCH /api/user/profile/
- user-by-id           -> GET    /api/user/by-id/?id=
- user-list-alt        -> GET    /api/user/list/

System:
- api-root             -> GET    /api/
- api-version          -> GET    /api/version/
- health-check         -> GET    /api/health/
"""


# ============================================
# ERROR HANDLING (Optional)
# ============================================

# Custom error handler views
@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def handler404(request, exception=None):
    """
    Custom 404 handler for API
    """
    return Response({
        'success': False,
        'message': 'Endpoint not found',
        'error': 'The requested resource was not found on this server.',
        'requested_url': request.path,
        'available_endpoints': '/api/',
        'suggestions': [
            'Use /api/users/ (plural) or /api/user/ (singular) for user operations',
            'Check the API root at /api/ for all available endpoints'
        ],
        'status_code': 404
    }, status=404)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def handler500(request):
    """
    Custom 500 handler for API
    """
    return Response({
        'success': False,
        'message': 'Internal server error',
        'error': 'An unexpected error occurred on the server.',
        'status_code': 500,
        'support': 'contact support@example.com'
    }, status=500)


# Django error handlers
handler404 = handler404
handler500 = handler500