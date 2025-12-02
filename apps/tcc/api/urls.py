from django.urls import path
from .views.user_view import *
from .views.auth_view import *
from django.http import JsonResponse

# Simple root view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def tcc_api_root(request):
    return JsonResponse({
        'message': 'TCC API Server is running',
        'version': '1.0.0',
        'status': 'operational',
        'endpoints': {
            'auth': {
                'login': '/tcc/auth/login/',
                'register': '/tcc/auth/register/',
            },
            'public_endpoints': [
                '/tcc/auth/login/',
                '/tcc/auth/register/',
                '/tcc/auth/forgot-password/',
                '/tcc/auth/reset-password/',
                '/tcc/users/create/',
                '/tcc/users/check-email/',
            ]
        }
    })

urlpatterns = [
    # Root endpoint
    path('', tcc_api_root, name='tcc-api-root'),
    
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
    path('users/<int:user_id>/status/', user_change_status_view, name='user-status'),
    path('users/bulk/status/', user_bulk_status_view, name='user-bulk-status'),
    path('users/change-password/', user_change_password_view, name='user-change-password'),
    path('users/verify-password/', user_verify_password_view, name='user-verify-password'),
    path('users/check-email/', user_check_email_view, name='user-check-email'),
    path('users/request-password-reset/', user_request_password_reset_view, name='user-request-password-reset'),
    path('users/reset-password/', user_reset_password_view, name='user-reset-password'),
]