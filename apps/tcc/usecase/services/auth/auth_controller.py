import logging
from typing import Dict, Any, Optional
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.auth_exceptions import AuthExceptionHandler
from apps.tcc.usecase.usecases.auth.login_uc import LoginUseCase
from apps.tcc.usecase.usecases.auth.logout_uc import LogoutUseCase
from apps.tcc.usecase.usecases.auth.refresh_uc import RefreshTokenUseCase
from apps.tcc.usecase.usecases.auth.verify_uc import VerifyTokenUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService

logger = logging.getLogger(__name__)


class AuthController(BaseController):
    """
    Authentication Controller
    Handles all authentication operations using auth use cases
    Integrated with AsyncAuthDomainService for audit logging and token management
    """

    def __init__(
        self,
        user_repository: UserRepository,
        auth_service: AsyncAuthDomainService,
        jwt_provider
    ):
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.jwt_provider = jwt_provider
        
        # Initialize all auth use cases with the shared auth service
        self.login_uc = LoginUseCase(jwt_provider, auth_service)
        self.logout_uc = LogoutUseCase(auth_service)
        self.refresh_uc = RefreshTokenUseCase(user_repository, jwt_provider)
        self.verify_uc = VerifyTokenUseCase()

    # LOGIN Operation
    @BaseController.handle_exceptions
    async def login(
        self, 
        input_data: Dict[str, Any], 
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        User login with email and password
        Uses: LoginUseCase (which uses AsyncAuthDomainService internally)
        """
        # Extract request metadata for audit logging
        request_meta = self._extract_request_meta(context)
        
        # Pass context to use case for comprehensive audit logging
        enhanced_context = {**(context or {}), 'request_meta': request_meta}
        result = await self.login_uc.execute(input_data, None, enhanced_context)
        return result

    # LOGOUT Operation  
    @BaseController.handle_exceptions
    async def logout(
        self,
        input_data: Dict[str, Any],
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        User logout with token revocation
        Uses: LogoutUseCase (which uses AsyncAuthDomainService internally)
        """
        # Extract request metadata for audit logging
        request_meta = self._extract_request_meta(context)
        
        enhanced_context = {**(context or {}), 'request_meta': request_meta}
        result = await self.logout_uc.execute(input_data, current_user, enhanced_context)
        return result

    # REFRESH Operation
    @BaseController.handle_exceptions
    async def refresh_token(
        self, 
        input_data: Dict[str, Any], 
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Refresh access token using refresh token
        Uses: RefreshTokenUseCase
        """
        result = await self.refresh_uc.execute(input_data, None, context or {})
        return result

    # VERIFY Operation
    @BaseController.handle_exceptions
    async def verify_token(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Verify token validity and get user data
        Uses: VerifyTokenUseCase
        """
        result = await self.verify_uc.execute({}, current_user, context or {})
        return result

    # DIRECT SERVICE OPERATIONS (using AsyncAuthDomainService directly when needed)
    
    async def revoke_token_direct(
        self,
        token: str,
        user_id: Optional[int] = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Direct token revocation using AsyncAuthDomainService
        Useful for admin operations or bulk token management
        """
        try:
            success = await self.auth_service.revoke_token_async(token, user_id)
            
            if success:
                return APIResponse.success_response(
                    message="Token revoked successfully",
                    data={"token_revoked": True}
                )
            else:
                return APIResponse.error_response(
                    message="Token revocation failed",
                    error_code="TOKEN_REVOCATION_FAILED",
                    status_code=400
                )
                
        except Exception as e:
            logger.error(f"Direct token revocation failed: {str(e)}")
            return APIResponse.error_response(
                message="Token revocation error",
                error_code="REVOCATION_ERROR",
                status_code=500
            )

    async def audit_security_event(
        self,
        user_id: int,
        event_type: str,
        description: str,
        severity: str = "MEDIUM",
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Log security events directly using AsyncAuthDomainService
        Useful for custom security monitoring
        """
        try:
            await self.auth_service._create_security_event_async(
                user_id=user_id,
                event_type=event_type,
                description=description,
                severity=severity
            )
            
            return APIResponse.success_response(
                message="Security event logged successfully"
            )
            
        except Exception as e:
            logger.error(f"Security event logging failed: {str(e)}")
            return APIResponse.error_response(
                message="Security event logging failed",
                error_code="AUDIT_LOG_ERROR",
                status_code=500
            )

    # HELPER METHODS
    def _extract_request_meta(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract request metadata from context for audit logging"""
        if not context or 'request' not in context:
            return {}
            
        request = context.get('request')
        if not request:
            return {}
            
        return {
            'HTTP_X_FORWARDED_FOR': request.META.get('HTTP_X_FORWARDED_FOR'),
            'REMOTE_ADDR': request.META.get('REMOTE_ADDR'),
            'HTTP_USER_AGENT': request.META.get('HTTP_USER_AGENT'),
            'HTTP_REFERER': request.META.get('HTTP_REFERER'),
            'SERVER_NAME': request.META.get('SERVER_NAME'),
        }


# Enhanced factory function with proper service initialization
def create_auth_controller(
    user_repository: UserRepository,
    auth_service: AsyncAuthDomainService,
    jwt_provider
) -> AuthController:
    """Factory function to create auth controller with integrated services"""
    return AuthController(user_repository, auth_service, jwt_provider)


# Legacy compatibility - maintain the existing AuthController interface if needed
class LegacyAuthController:
    """
    Maintains compatibility with existing code that uses the old AuthController interface
    Can be deprecated over time
    """
    
    def __init__(self, create_user_uc, login_user_uc, get_user_uc=None, update_user_uc=None):
        # Initialize with minimal dependencies for backward compatibility
        self.create_user_uc = create_user_uc
        self.login_user_uc = login_user_uc
        self.get_user_uc = get_user_uc
        self.update_user_uc = update_user_uc
        self.auth_domain_service = AsyncAuthDomainService()
    
    async def register_user(self, user_data: dict) -> APIResponse:
        """Legacy registration method - delegates to user controller"""
        # This would typically call user creation use cases
        # Maintained for backward compatibility
        pass
    
    async def login_user(self, login_data: dict, request_meta: Optional[Dict] = None) -> APIResponse:
        """Legacy login method"""
        # Create a minimal context for the legacy interface
        context = {'request_meta': request_meta} if request_meta else {}
        
        # Use the new unified controller internally
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),
            jwt_provider=None  # Would need to be provided
        )
        
        return await controller.login(login_data, context)
    
    async def logout_user(self, token: str, user_id: Optional[int] = None) -> APIResponse:
        """Legacy logout method"""
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),
            jwt_provider=None
        )
        
        return await controller.revoke_token_direct(token, user_id)