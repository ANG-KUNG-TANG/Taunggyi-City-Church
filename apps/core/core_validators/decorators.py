from functools import wraps
from typing import Type, Any, Dict
from pydantic import BaseModel, ValidationError
from django.http import JsonResponse
from rest_framework import status

from apps.core.schemas.input_schemas.auth import (
    LoginInputSchema, RegisterInputSchema, RefreshTokenInputSchema,
    LogoutInputSchema, ForgotPasswordInputSchema, ResetPasswordInputSchema,
    ChangePasswordInputSchema, VerifyEmailInputSchema, ResendVerificationInputSchema
)
from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema, UserUpdateInputSchema, UserQueryInputSchema
)

def validate_input(schema_class: Type[BaseModel]):
    """
    Decorator to validate input data against a Pydantic schema
    """
    def decorator(view_func):
        @wraps(view_func)
        async def _wrapped_view(self, *args, **kwargs):
            try:
                # Extract input data from appropriate location
                request = None
                input_data = {}
                
                # Find request object in args or kwargs
                for arg in args:
                    if hasattr(arg, 'data'):
                        request = arg
                        break
                
                if not request:
                    for key, value in kwargs.items():
                        if hasattr(value, 'data'):
                            request = value
                            break
                
                if request and hasattr(request, 'data'):
                    input_data = request.data
                
                # Validate data against schema
                validated_data = schema_class(**input_data)
                
                # Replace the input data with validated data
                if 'input_data' in kwargs:
                    kwargs['input_data'] = validated_data
                else:
                    # If using self, we need to handle differently
                    if args and hasattr(args[0], 'validated_data'):
                        args[0].validated_data = validated_data
                
                return await view_func(self, *args, **kwargs)
                
            except ValidationError as e:
                return JsonResponse(
                    {
                        "error": "Validation failed",
                        "details": e.errors(),
                        "message": "Invalid input data"
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            except Exception as e:
                return JsonResponse(
                    {
                        "error": "Validation error",
                        "details": str(e),
                        "message": "Input validation failed"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        return _wrapped_view
    return decorator

# Specific validation decorators for common operations
def validate_user_create(view_func):
    """Validate user creation input"""
    return validate_input(UserCreateInputSchema)(view_func)

def validate_user_update(view_func):
    """Validate user update input"""
    return validate_input(UserUpdateInputSchema)(view_func)

def validate_user_query(view_func):
    """Validate user query parameters"""
    return validate_input(UserQueryInputSchema)(view_func)

def validate_login(view_func):
    """Validate login input"""
    return validate_input(LoginInputSchema)(view_func)

def validate_register(view_func):
    """Validate registration input"""
    return validate_input(RegisterInputSchema)(view_func)

def validate_refresh_token(view_func):
    """Validate refresh token input"""
    return validate_input(RefreshTokenInputSchema)(view_func)

def validate_logout(view_func):
    """Validate logout input"""
    return validate_input(LogoutInputSchema)(view_func)

def validate_forgot_password(view_func):
    """Validate forgot password input"""
    return validate_input(ForgotPasswordInputSchema)(view_func)

def validate_reset_password(view_func):
    """Validate reset password input"""
    return validate_input(ResetPasswordInputSchema)(view_func)

def validate_change_password(view_func):
    """Validate change password input"""
    return validate_input(ChangePasswordInputSchema)(view_func)

# Permission decorators
def require_admin(view_func):
    """Require admin permissions"""
    @wraps(view_func)
    async def _wrapped_view(self, *args, **kwargs):
        # This would typically check user permissions
        # For now, it's a placeholder that passes through
        return await view_func(self, *args, **kwargs)
    return _wrapped_view

def require_member(view_func):
    """Require member permissions"""
    @wraps(view_func)
    async def _wrapped_view(self, *args, **kwargs):
        # This would typically check user is authenticated
        # For now, it's a placeholder that passes through
        return await view_func(self, *args, **kwargs)
    return _wrapped_view