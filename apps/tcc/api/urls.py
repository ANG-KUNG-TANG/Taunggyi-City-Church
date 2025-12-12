from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Import user views from the correct location
try:
    # Try importing from the updated location (based on your controller structure)
    from views.user_view import (
        # User views
        health_check_view,
        create_user_view,
        get_current_user_profile_view,
        get_user_by_id_view,
        get_user_by_email_view,
        get_all_users_view,
        get_users_by_role_view,
        search_users_view,
        update_user_view,
        update_current_user_profile_view,
        change_user_status_view,
        check_email_availability_view,
        delete_user_view,
    )
except ImportError:
    # Fallback: Import from views directory if the above doesn't work
    from .views.user_view import (
        health_check_view,
        create_user_view,
        get_current_user_profile_view,
        get_user_by_id_view,
        get_user_by_email_view,
        get_all_users_view,
        get_users_by_role_view,
        search_users_view,
        update_user_view,
        update_current_user_profile_view,
        change_user_status_view,
        check_email_availability_view,
        delete_user_view,
    )

# Import auth views - you need to create these or update imports
try:
    from .views.auth_view import (
        login_view,
        register_view,
        logout_view,
        refresh_token_view,
        verify_token_view,
        forgot_password_view,
        reset_password_view,
        user_sessions_view,
        revoke_session_view,
        revoke_all_sessions_view,
    )
except ImportError:
    # Placeholder imports - you'll need to create these auth views
    from .views.auth_view import (
        login_view,
        register_view,
        logout_view,
        refresh_token_view,
        verify_token_view,
        forgot_password_view,
        reset_password_view,
        user_sessions_view,
        revoke_session_view,
        revoke_all_sessions_view,
    )


# Simple root view
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
                'logout': '/tcc/auth/logout/',
                'refresh': '/tcc/auth/refresh/',
                'verify': '/tcc/auth/verify/',
                'forgot_password': '/tcc/auth/forgot-password/',
                'reset_password': '/tcc/auth/reset-password/',
                'sessions': '/tcc/auth/sessions/',
            },
            'users': {
                'create': '/tcc/users/',
                'current_profile': '/tcc/users/me/',
                'user_by_id': '/tcc/users/{id}/',
                'user_by_email': '/tcc/users/by-email/',
                'all_users': '/tcc/users/all/',
                'users_by_role': '/tcc/users/role/{role}/',
                'search_users': '/tcc/users/search/',
                'update_user': '/tcc/users/{id}/update/',
                'update_profile': '/tcc/users/me/update/',
                'change_status': '/tcc/users/{id}/status/',
                'check_email': '/tcc/users/check-email/',
                'delete_user': '/tcc/users/{id}/delete/',
                'health': '/tcc/health/',
            }
        }
    })


urlpatterns = [
    # Root endpoint
    path('', tcc_api_root, name='tcc-api-root'),
    
    # Health check endpoint (should be at root level)
    path('health/', health_check_view, name='health-check'),
    
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
    path('users/', create_user_view, name='create-user'),
    path('users/me/', get_current_user_profile_view, name='current-user-profile'),
    path('users/<int:user_id>/', get_user_by_id_view, name='user-by-id'),
    path('users/by-email/', get_user_by_email_view, name='user-by-email'),
    path('users/all/', get_all_users_view, name='all-users'),
    path('users/role/<str:role>/', get_users_by_role_view, name='users-by-role'),
    path('users/search/', search_users_view, name='search-users'),
    path('users/<int:user_id>/update/', update_user_view, name='update-user'),
    path('users/me/update/', update_current_user_profile_view, name='update-current-user'),
    path('users/<int:user_id>/status/', change_user_status_view, name='change-user-status'),
    path('users/check-email/', check_email_availability_view, name='check-email'),
    path('users/<int:user_id>/delete/', delete_user_view, name='delete-user'),
]