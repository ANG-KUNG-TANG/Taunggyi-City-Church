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
                
                # Admin User Creation (via ViewSet - standard REST)
                'admin_create': f'{base_url}/users/',
                
                # Admin User Creation (flexible with role parameter)
                'admin_create_flexible': f'{base_url}/users/create-by-admin/',
                
                # User Profile & Management
                'profile': f'{base_url}/users/profile/',
                'email_check': f'{base_url}/users/check-email/',
                'list_all': f'{base_url}/users/',
                
                # Individual User Operations
                'user_operations': {
                    'retrieve': f'{base_url}/users/{{id}}/',
                    'update': f'{base_url}/users/{{id}}/',
                    'partial_update': f'{base_url}/users/{{id}}/',
                    'delete': f'{base_url}/users/{{id}}/',
                    'change_status': f'{base_url}/users/{{id}}/change_status/'
                },
                
                # Search & Filter Operations
                'search_operations': {
                    'by_email': f'{base_url}/users/by_email/?email=',
                    'by_role': f'{base_url}/users/by_role/?role=',
                    'search': f'{base_url}/users/search/?q='
                },
                
                # Bulk Operations
                'bulk_operations': {
                    'bulk_delete': f'{base_url}/users/bulk_delete/'
                },
                
                # Alternative Views
                'alternative_list': f'{base_url}/users/list/'
            },
            
            # System
            'system': {
                'health_check': f'{base_url}/health/',
                'api_root': f'{base_url}/'
            }
        },
        'user_creation_methods': {
            'public_registration': {
                'endpoint': f'{base_url}/users/register/',
                'method': 'POST',
                'permissions': 'Public',
                'purpose': 'Regular users self-registration',
                'default_role': 'VISITOR',
                'required_fields': ['email', 'password', 'first_name', 'last_name'],
                'note': 'No authentication required'
            },
            'admin_create_standard': {
                'endpoint': f'{base_url}/users/',
                'method': 'POST',
                'permissions': 'Admin only',
                'purpose': 'Standard REST admin user creation (always creates admin)',
                'default_role': 'ADMIN',
                'required_fields': ['email', 'password', 'first_name', 'last_name'],
                'note': 'Uses UserViewSet create method, always creates ADMIN users'
            },
            'admin_create_flexible': {
                'endpoint': f'{base_url}/users/create-by-admin/',
                'method': 'POST',
                'permissions': 'Admin only',
                'purpose': 'Flexible admin creation with role parameter',
                'parameters': {
                    'role': 'staff or admin (default: staff)'
                },
                'required_fields': ['email', 'password', 'first_name', 'last_name'],
                'note': 'Allows creating both STAFF and ADMIN users via role parameter'
            }
        },
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
# ROUTER SETUP
# ============================================

# Create main router
router = DefaultRouter(trailing_slash=False)

# Register UserViewSet - This provides CRUD operations
router.register(r'users', UserViewSet, basename='user')

# The router will create these URLs automatically:
# GET    /api/users          -> list
# POST   /api/users          -> create (creates ADMIN users by default)
# GET    /api/users/{pk}     -> retrieve
# PUT    /api/users/{pk}     -> update
# PATCH  /api/users/{pk}     -> partial_update
# DELETE /api/users/{pk}     -> destroy

# Custom actions from UserViewSet (configured via @action decorator):
# GET    /api/users/by_email     -> by_email
# GET    /api/users/search       -> search
# GET    /api/users/by_role      -> by_role
# POST   /api/users/bulk_delete  -> bulk_delete
# PATCH  /api/users/{pk}/change_status -> change_status


# ============================================
# URL PATTERNS
# ============================================

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
    
    # ========================================
    # USER MANAGEMENT ENDPOINTS
    # ========================================
    path('users/', include([
        # Public Registration (No authentication required)
        path('register/', RegisterView.as_view(), name='user-register'),
        
        # Admin-only User Creation with Role Parameter
        # Note: Since create_by_admin is an @action, we need to use as_view with method mapping
        path('create-by-admin/', 
             RegisterView.as_view(), 
             name='user-create-by-admin'),
        
        # Email Availability Check (Public)
        path('check-email/', EmailAvailabilityView.as_view(), name='user-check-email'),
        
        # User Profile (Authenticated)
        path('profile/', ProfileView.as_view(), name='user-profile'),
        
        # Alternative List View
        path('list/', UserListView.as_view(), name='user-list-alt'),
        
        # Include ViewSet URLs (CRUD operations)
        # This includes: /users/, /users/{id}/, and all @action endpoints
        path('', include(router.urls)),
    ])),
]


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

Authentication:
- auth-login           -> POST   /api/auth/login/
- auth-logout          -> POST   /api/auth/logout/
- auth-refresh         -> POST   /api/auth/refresh/
- auth-verify          -> POST   /api/auth/verify/
- auth-forgot-password -> POST   /api/auth/forgot-password/
- auth-reset-password  -> POST   /api/auth/reset-password/
- auth-change-password -> POST   /api/auth/change-password/
- auth-status          -> GET    /api/auth/status/

User Management:
- user-register        -> POST   /api/users/register/ (Public)
- user-create-by-admin -> POST   /api/users/create-by-admin/ (Admin only, flexible role)
- user-check-email     -> GET    /api/users/check-email/ (Public)
- user-profile         -> GET/PUT/PATCH /api/users/profile/ (Authenticated)
- user-list-alt        -> GET    /api/users/list/ (Alternative list)

UserViewSet (router-generated):
- user-list            -> GET    /api/users
- user-detail          -> GET    /api/users/{id}
- user-create          -> POST   /api/users (Admin only, creates ADMIN users)
- user-update          -> PUT    /api/users/{id}
- user-partial-update  -> PATCH  /api/users/{id}
- user-delete          -> DELETE /api/users/{id}
- user-by-email        -> GET    /api/users/by_email
- user-search          -> GET    /api/users/search
- user-by-role         -> GET    /api/users/by_role
- user-bulk-delete     -> POST   /api/users/bulk_delete
- user-change-status   -> PATCH  /api/users/{id}/change_status

System:
- api-root             -> GET    /api/
- api-version          -> GET    /api/version/
- health-check         -> GET    /api/health/
"""


# ============================================
# API DOCUMENTATION
# ============================================
"""
COMPREHENSIVE USER CREATION API DOCUMENTATION

Three ways to create users:

1. PUBLIC REGISTRATION (No auth required)
   Endpoint: POST /api/users/register/
   Purpose: Self-registration for regular users
   Defaults: role=VISITOR, status=PENDING
   Example Request:
     POST /api/users/register/
     {
       "email": "user@example.com",
       "password": "Password123!",
       "first_name": "John",
       "last_name": "Doe",
       "phone": "+1234567890"
     }

2. ADMIN CREATE - STANDARD (Admin auth required)
   Endpoint: POST /api/users/
   Purpose: Standard REST admin user creation
   Defaults: role=ADMIN, status=ACTIVE
   Note: Always creates ADMIN users
   Example Request:
     POST /api/users/
     Headers: Authorization: Bearer <admin_token>
     {
       "email": "admin@example.com",
       "password": "AdminPass123!",
       "first_name": "Admin",
       "last_name": "User"
     }

3. ADMIN CREATE - FLEXIBLE (Admin auth required)
   Endpoint: POST /api/users/create-by-admin/
   Purpose: Flexible admin creation with role parameter
   Parameters: role (staff/admin, default: staff)
   Example - Create staff:
     POST /api/users/create-by-admin/
     Headers: Authorization: Bearer <admin_token>
     {
       "email": "staff@example.com",
       "password": "StaffPass123!",
       "first_name": "Jane",
       "last_name": "Smith",
       "role": "staff"
     }
   Example - Create admin:
     POST /api/users/create-by-admin/
     Headers: Authorization: Bearer <admin_token>
     {
       "email": "admin2@example.com",
       "password": "AdminPass456!",
       "first_name": "Another",
       "last_name": "Admin",
       "role": "admin"
     }

Key Differences:
- /users/register/         -> Public, creates VISITOR
- /users/                  -> Admin only, creates ADMIN (standard REST)
- /users/create-by-admin/  -> Admin only, creates STAFF or ADMIN based on role parameter

All endpoints check for duplicate emails and return 409 Conflict if user already exists.
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