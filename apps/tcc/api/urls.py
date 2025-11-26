from django.urls import path
from .views.user_view import (
    UserCreateView, UserProfileView, UserDetailView, 
    UserListView, UserAdminView, UserBulkView, UserByEmailView
)
from .views.auth_view import (
    LoginView,    LogoutView,    RefreshTokenView,
    VerifyTokenView,
    AdminTokenRevocationView,
    SecurityEventView,
    AuditLogsView,
    ProtectedView
)

urlpatterns = [
    # Core authentication endpoints
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/verify/', VerifyTokenView.as_view(), name='auth-verify'),
    
    # Admin & security endpoints
    path('auth/admin/revoke-token/', AdminTokenRevocationView.as_view(), name='admin-revoke-token'),
    path('auth/admin/security-events/', SecurityEventView.as_view(), name='security-events'),
    path('auth/admin/audit-logs/', AuditLogsView.as_view(), name='audit-logs'),
    
    # Protected resource examples
    path('auth/protected/', ProtectedView.as_view(), name='auth-protected'),
]
urlpatterns = [
    # Public
    path('users/', UserCreateView.as_view(), name='user-create'),
    
    # Current user
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    
    # Specific user
    path('users/<str:user_id>/', UserDetailView.as_view(), name='user-detail'),
    
    # Listing & search
    path('users/list/', UserListView.as_view(), name='user-list'),
    
    # Admin operations
    path('users/<str:user_id>/status/', UserAdminView.as_view(), name='user-status'),
    path('users/bulk/status/', UserBulkView.as_view(), name='user-bulk-status'),
    path('users/by-email/', UserByEmailView.as_view(), name='user-by-email'),
]