import asyncio
import logging
from functools import wraps
from typing import Dict, Any, Optional

from asgiref.sync import sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.core.schemas.common.response import APIResponse, UserRegistrationResponse
from apps.core.schemas.schemas.users import UserCreateSchema, UserLoginSchema
from apps.tcc.models.audit.audit import AuditLog, SecurityEvent
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserAlreadyExistsException, 
    UserNotFoundException,
    InvalidCredentialsException,
    AccountLockedException
)

logger = logging.getLogger(__name__)


class AsyncAuthDomainService:
    """Domain service for authentication-related operations with audit logging"""
    
    @sync_to_async
    def revoke_token_async(self, token: str, user_id: Optional[int] = None) -> bool:
        """Async token revocation with audit logging"""
        try:
            refresh_token = RefreshToken(token)
            user_id_from_token = refresh_token.get('user_id', user_id)
            refresh_token.blacklist()
            
            # Log successful token revocation
            self._create_security_event_async(
                user_id=user_id_from_token,
                event_type='TOKEN_REVOKED',
                description='Refresh token revoked during logout'
            )
            return True
        except Exception as e:
            # Log failed revocation attempt
            self._create_security_event_async(
                user_id=user_id,
                event_type='TOKEN_REVOCATION_FAILED',
                description=f'Token revocation failed: {str(e)}',
                severity='HIGH'
            )
            logger.error(f"Token revocation failed: {str(e)}")
            return False
    
    @sync_to_async
    def audit_login_async(self, user_id: int, action: str, request_meta: Optional[Dict] = None) -> None:
        """Async audit logging with request context"""
        try:
            ip_address = None
            user_agent = None
            metadata = {}
            
            if request_meta:
                ip_address = self._get_client_ip(request_meta)
                user_agent = request_meta.get('HTTP_USER_AGENT', '')[:500]  # Limit length
                metadata = {
                    'http_referer': request_meta.get('HTTP_REFERER', ''),
                    'server_name': request_meta.get('SERVER_NAME', ''),
                }
            
            AuditLog.objects.create(
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Audit logging failed: {str(e)}")
            # Create security event for audit failure
            self._create_security_event_async(
                user_id=user_id,
                event_type='AUDIT_LOG_FAILED',
                description=f'Audit logging failed: {str(e)}',
                severity='MEDIUM'
            )
    
    def _get_client_ip(self, request_meta: Dict) -> str:
        """Extract client IP from request metadata"""
        x_forwarded_for = request_meta.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request_meta.get('REMOTE_ADDR', '')
        return ip
    
    @sync_to_async
    def _create_security_event_async(self, user_id: int, event_type: str, 
                                   description: str, severity: str = 'MEDIUM') -> None:
        """Create security event log"""
        try:
            SecurityEvent.objects.create(
                user_id=user_id,
                event_type=event_type,
                description=description,
                severity=severity,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Security event creation failed: {str(e)}")


def handle_auth_exceptions(func):
    """
    Decorator to handle authentication-related exceptions
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except UserAlreadyExistsException as e:
            logger.warning(f"User already exists: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Registration failed",
                error_code="USER_ALREADY_EXISTS",
                status_code=409,
                details=e.details,
                user_message=e.user_message
            )
        except InvalidUserInputException as e:
            logger.warning(f"Invalid user input: {e.field_errors}")
            return UserRegistrationResponse.error_response(
                message="Validation failed",
                error_code="INVALID_INPUT",
                status_code=422,
                details={"field_errors": e.field_errors, **e.details},
                user_message=e.user_message
            )
        except InvalidCredentialsException as e:
            logger.warning(f"Invalid credentials: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Authentication failed",
                error_code="INVALID_CREDENTIALS",
                status_code=401,
                details=e.details,
                user_message=e.user_message
            )
        except AccountLockedException as e:
            logger.warning(f"Account locked: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Account locked",
                error_code="ACCOUNT_LOCKED",
                status_code=423,
                details=e.details,
                user_message=e.user_message
            )
        except UserNotFoundException as e:
            logger.warning(f"User not found: {e.details}")
            return UserRegistrationResponse.error_response(
                message="User not found",
                error_code="USER_NOT_FOUND",
                status_code=404,
                details=e.details,
                user_message=e.user_message
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return UserRegistrationResponse.error_response(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                status_code=500,
                details={"error": str(e)},
                user_message="An unexpected error occurred. Please try again later."
            )
    return wrapper


class AuthController:
    """
    Unified authentication controller with validation, exception handling, and audit logging
    """

    def __init__(self, create_user_uc, login_user_uc, get_user_uc=None, update_user_uc=None):
        self.create_user_uc = create_user_uc
        self.login_user_uc = login_user_uc
        self.get_user_uc = get_user_uc
        self.update_user_uc = update_user_uc
        self.auth_domain_service = AsyncAuthDomainService()

    @handle_auth_exceptions
    async def register_user(self, user_data: dict) -> UserRegistrationResponse:
        """
        Register user with validation and exception handling
        """
        # Schema validation should happen in the use case or via decorator
        result = await self.create_user_uc.execute(user_data)
        
        # Audit registration if successful
        if result.success and hasattr(result, 'user_id'):
            await self.auth_domain_service.audit_login_async(
                user_id=result.user_id,
                action='REGISTER'
            )
        
        return result

    @handle_auth_exceptions
    async def login_user(self, login_data: dict, request_meta: Optional[Dict] = None) -> UserRegistrationResponse:
        """
        User login with validation, exception handling, and audit logging
        """
        result = await self.login_user_uc.execute(login_data)
        
        # Audit successful login
        if result.success and hasattr(result, 'user_id'):
            await self.auth_domain_service.audit_login_async(
                user_id=result.user_id,
                action='LOGIN',
                request_meta=request_meta
            )
        
        return result

    async def logout_user(self, token: str, user_id: Optional[int] = None) -> APIResponse:
        """
        Logout user by revoking token with audit logging
        """
        success = await self.auth_domain_service.revoke_token_async(token, user_id)
        
        if success:
            return APIResponse.success_response(message="Logout successful")
        else:
            return APIResponse.error_response(
                message="Logout failed",
                error_code="TOKEN_REVOCATION_FAILED",
                status_code=400
            )

    @handle_auth_exceptions
    async def get_user_profile(self, user_id: int) -> UserRegistrationResponse:
        """
        Get user profile with exception handling
        """
        if not self.get_user_uc:
            raise NotImplementedError("Get user use case not provided")
        
        return await self.get_user_uc.execute({"user_id": user_id})

    @handle_auth_exceptions
    async def update_user_profile(self, user_id: int, update_data: dict) -> UserRegistrationResponse:
        """
        Update user profile with validation
        """
        if not self.update_user_uc:
            raise NotImplementedError("Update user use case not provided")
        
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": update_data
        })


# Convenience function for direct login usage
async def login(request, login_uc) -> APIResponse:
    """
    Convenience function for login requests
    """
    controller = AuthController(None, login_uc)
    
    ctx = {
        'request_meta': {
            'HTTP_X_FORWARDED_FOR': request.META.get('HTTP_X_FORWARDED_FOR'),
            'REMOTE_ADDR': request.META.get('REMOTE_ADDR'),
            'HTTP_USER_AGENT': request.META.get('HTTP_USER_AGENT'),
            'HTTP_REFERER': request.META.get('HTTP_REFERER'),
            'SERVER_NAME': request.META.get('SERVER_NAME'),
        }
    }
    
    result = await controller.login_user(request.data, ctx['request_meta'])
    
    if result.success:
        return APIResponse.success_response(message="Login successful", data=result.data)
    else:
        return APIResponse.error_response(
            message=result.message,
            error_code=result.error_code,
            status_code=result.status_code,
            details=result.details
        )