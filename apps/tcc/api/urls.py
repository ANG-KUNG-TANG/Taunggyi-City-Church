"""
URL Configuration - Standard DRF Routing
Clean, organized, and follows Django/DRF best practices
"""
import traceback
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

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
    return Response({
        'message': 'TCC API Server',
        'version': '1.0.0',
        'status': 'operational',
        'endpoints': {
            'auth': {
                'login': '/api/auth/login/',
                'logout': '/api/auth/logout/',
                'refresh': '/api/auth/refresh/',
                'verify': '/api/auth/verify/',
                'forgot_password': '/api/auth/forgot-password/',
                'reset_password': '/api/auth/reset-password/',
            },
            'users': {
                'register': '/api/users/register/',
                'profile': '/api/users/profile/',
                'check_email': '/api/users/check-email/',
                'list': '/api/users/',
                'detail': '/api/users/{id}/',
                'by_email': '/api/users/by_email/?email=',
                'search': '/api/users/search/?q=',
            },
            'health': '/api/health/',
        },
        'documentation': 'Visit /api/docs/ for API documentation'
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
    print("DEBUG: Successfully imported all auth views!")  # ADD THIS
    auth_views_available = True
except ImportError as e:
    print(f"DEBUG: Import failed with error: {e}")  # ADD THIS
    print(f"DEBUG: Full traceback:")  # ADD THIS
    traceback.print_exc()  # ADD THIS
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
                'message': 'This endpoint is not yet available'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
        
        def post(self, request):
            return Response({
                'error': 'Endpoint not implemented',
                'message': 'This endpoint is not yet available'
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

# Create router for ViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

# The router will create these URLs automatically:
# GET    /users/          -> list
# POST   /users/          -> create
# GET    /users/{pk}/     -> retrieve
# PUT    /users/{pk}/     -> update
# PATCH  /users/{pk}/     -> partial_update
# DELETE /users/{pk}/     -> destroy
# GET    /users/by_email/ -> custom action
# GET    /users/search/   -> custom action


# ============================================
# URL PATTERNS
# ============================================

urlpatterns = [
    # ========================================
    # ROOT & HEALTH
    # ========================================
    path('', api_root, name='api-root'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # ========================================
    # AUTHENTICATION ENDPOINTS
    # ========================================
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/verify/', VerifyTokenView.as_view(), name='auth-verify'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
    
    # ========================================
    # USER ENDPOINTS (Non-ViewSet)
    # ========================================
    
    # Public endpoints
    path('users/register/', RegisterView.as_view(), name='user-register'),
    path('users/check-email/', EmailAvailabilityView.as_view(), name='user-check-email'),
    
    # Authenticated endpoints
    path('users/profile/', ProfileView.as_view(), name='user-profile'),
    path('users/list/', UserListView.as_view(), name='user-list-alt'),  # Alternative to ViewSet list
    
    # ========================================
    # USER VIEWSET ENDPOINTS
    # ========================================
    # Include router URLs for full CRUD operations
    path('', include(router.urls)),
]


# ============================================
# URL NAMING CONVENTION
# ============================================
"""
Standard URL naming generated by router:
- user-list         -> GET /users/
- user-detail       -> GET /users/{pk}/
- user-by-email     -> GET /users/by_email/
- user-search       -> GET /users/search/

Custom URL naming:
- api-root          -> GET /
- health-check      -> GET /health/
- auth-login        -> POST /auth/login/
- auth-logout       -> POST /auth/logout/
- user-register     -> POST /users/register/
- user-profile      -> GET/PUT/PATCH /users/profile/
- user-check-email  -> GET /users/check-email/
"""