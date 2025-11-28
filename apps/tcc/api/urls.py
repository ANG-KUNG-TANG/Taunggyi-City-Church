from django.urls import path
from .views.user_view import *
from .views.auth_view import *

urlpatterns = [
    # Auth endpoints
    path('auth/login/', login_view, name='auth-login'),
    path('auth/register/', register_view, name='auth-register'),
    path('auth/logout/', logout_view, name='auth-logout'),
    path('auth/refresh/', refresh_token_view, name='auth-refresh'),
    path('auth/verify/', verify_token_view, name='auth-verify'),
    path('auth/forgot-password/', forgot_password_view, name='auth-forgot-password'),
    path('auth/reset-password/', reset_password_view, name='auth-reset-password'),

    # Session management endpoints
    path('auth/sessions/', user_sessions_view, name='user-sessions'),
    path('auth/sessions/<str:session_id>/revoke/', revoke_session_view, name='revoke-session'),
    path('auth/sessions/revoke-all/', revoke_all_sessions_view, name='revoke-all-sessions'),

    # User endpoints
    path('users/create/', user_create_view, name='user-create'),
    path('users/profile/', user_profile_view, name='user-profile'),
    path('users/<int:user_id>/', user_detail_view, name='user-detail'),
    path('users/', user_list_view, name='user-list'),
    path('users/by-email/', user_by_email_view, name='user-by-email'),
    path('users/<int:user_id>/status/', user_admin_view, name='user-status'),
    path('users/bulk/status/', user_bulk_view, name='user-bulk-status'),
]