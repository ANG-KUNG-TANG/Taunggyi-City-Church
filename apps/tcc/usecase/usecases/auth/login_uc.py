from typing import Dict, Any, Optional
from datetime import datetime
from apps.core.core_exceptions.domain import DomainException, DomainValidationException
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserNotFoundException,
    AccountLockedException
)
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.schemas.input_schemas.users import (
    UserLoginInputSchema,
    UserChangePasswordInputSchema,
    UserResetPasswordRequestInputSchema,
    UserResetPasswordInputSchema
)
from apps.core.schemas.out_schemas.user_out_schemas import (
    UserLoginResponseSchema,
    UserTokenRefreshResponseSchema,
    UserPasswordChangeResponseSchema,
    UserResetPasswordResponseSchema
)
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTAuthService
from apps.tcc.usecase.usecases.base.password_service import PasswordService
import logging

logger = logging.getLogger(__name__)

class LoginUserUseCase(BaseUseCase):
    """Login user with email and password"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.jwt_service = dependencies.get('jwt_service', JWTAuthService())
        self.password_service = dependencies.get('password_service', PasswordService())
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Login doesn't require auth
        self.config.validate_input = True
        self.config.audit_log = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate login input"""
        try:
            UserLoginInputSchema(**input_data)
        except Exception as e:
            logger.error(f"Login validation failed: {str(e)}")
            raise DomainValidationException(
                message="Invalid login data",
                user_message="Please check your email and password."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserLoginResponseSchema:
        """Execute login with email and password"""
        login_input = UserLoginInputSchema(**input_data)
        
        # 1. Get user by email with password hash
        user_entity = await self.user_repository.get_by_email(
            login_input.email,
            include_password_hash=True
        )
        
        if not user_entity:
            raise DomainValidationException(
                message="Invalid credentials",
                user_message="Invalid email or password."
            )
        
        # 2. Check if account is locked
        if hasattr(user_entity, 'is_locked') and user_entity.is_locked:
            raise AccountLockedException(
                user_id=str(user_entity.id),
                lock_reason="Account locked due to security reasons",
                user_message="Your account is locked. Please contact support."
            )
        
        # 3. Verify password
        if not hasattr(user_entity, 'password_hash') or not user_entity.password_hash:
            raise DomainValidationException(
                message="Invalid credentials",
                user_message="Invalid email or password."
            )
        
        password_valid = await self.password_service.verify_password(
            login_input.password,
            user_entity.password_hash
        )
        
        if not password_valid:
            # Track failed attempts (optional)
            await self._handle_failed_login(user_entity.id)
            raise DomainValidationException(
                message="Invalid credentials",
                user_message="Invalid email or password."
            )
        
        # 4. Reset failed login attempts on successful login
        await self._reset_failed_logins(user_entity.id)
        
        # 5. Generate JWT tokens
        user_roles = [user_entity.role] if hasattr(user_entity, 'role') else []
        
        access_token = await self.jwt_service.generate_access_token(
            user_id=user_entity.id,
            email=user_entity.email,
            roles=user_roles
        )
        
        refresh_token, token_id = await self.jwt_service.generate_refresh_token(
            user_id=user_entity.id
        )
        
        # 6. Update user last login
        await self.user_repository.update(user_entity.id, {
            'last_login': datetime.utcnow(),
            'login_count': getattr(user_entity, 'login_count', 0) + 1
        })
        
        # 7. Log successful login
        logger.info(f"User {user_entity.email} logged in successfully")
        
        return UserLoginResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes in seconds
            user=user_entity
        )
    
    async def _handle_failed_login(self, user_id: int):
        """Track failed login attempts"""
        # This could be implemented with cache or database
        # For simplicity, we'll just log it
        logger.warning(f"Failed login attempt for user ID: {user_id}")
    
    async def _reset_failed_logins(self, user_id: int):
        """Reset failed login counter"""
        # Implementation depends on your tracking system
        pass


class LogoutUserUseCase(BaseUseCase):
    """Logout user and blacklist tokens"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.jwt_service = dependencies.get('jwt_service', JWTAuthService())
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True
        self.config.audit_log = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate logout input"""
        refresh_token = input_data.get('refresh_token')
        
        if not refresh_token:
            raise DomainValidationException(
                message="Refresh token is required",
                user_message="Refresh token is missing."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Execute logout - blacklist refresh token"""
        refresh_token = input_data['refresh_token']
        
        # 1. Verify refresh token to get token ID
        refresh_payload = await self.jwt_service.verify_refresh_token(refresh_token)
        
        if not refresh_payload:
            raise DomainValidationException(
                message="Invalid refresh token",
                user_message="Invalid refresh token."
            )
        
        # 2. Blacklist the refresh token
        await self.jwt_service.blacklist_refresh_token(
            user_id=refresh_payload['user_id'],
            token_id=refresh_payload['jti']
        )
        
        # 3. Log logout event
        logger.info(f"User {refresh_payload['user_id']} logged out successfully")
        
        return {
            'success': True,
            'message': 'Logged out successfully'
        }


class RefreshTokenUseCase(BaseUseCase):
    """Refresh access token using refresh token"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.jwt_service = dependencies.get('jwt_service', JWTAuthService())
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Token refresh doesn't require auth
        self.config.validate_input = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate refresh token input"""
        refresh_token = input_data.get('refresh_token')
        
        if not refresh_token:
            raise DomainValidationException(
                message="Refresh token is required",
                user_message="Refresh token is missing."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserTokenRefreshResponseSchema:
        """Generate new access token using refresh token"""
        refresh_token = input_data['refresh_token']
        
        # 1. Verify refresh token
        refresh_payload = await self.jwt_service.verify_refresh_token(refresh_token)
        
        if not refresh_payload:
            raise DomainValidationException(
                message="Invalid or expired refresh token",
                user_message="Refresh token is invalid or expired. Please login again."
            )
        
        # 2. Get user data
        user_entity = await self.user_repository.get_by_id(refresh_payload['user_id'])
        
        if not user_entity or not hasattr(user_entity, 'is_active') or not user_entity.is_active:
            raise DomainValidationException(
                message="User not found or inactive",
                user_message="User account is not active."
            )
        
        # 3. Generate new access token
        user_roles = [user_entity.role] if hasattr(user_entity, 'role') else []
        
        new_access_token = await self.jwt_service.generate_access_token(
            user_id=user_entity.id,
            email=user_entity.email,
            roles=user_roles
        )
        
        return UserTokenRefreshResponseSchema(
            access_token=new_access_token,
            expires_in=900  # 15 minutes in seconds
        )


class ForgotPasswordUseCase(BaseUseCase):
    """Request password reset - sends reset token"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.jwt_service = dependencies.get('jwt_service', JWTAuthService())
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public endpoint
        self.config.validate_input = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate forgot password input"""
        try:
            UserResetPasswordRequestInputSchema(**input_data)
        except Exception as e:
            logger.error(f"Forgot password validation failed: {str(e)}")
            raise DomainValidationException(
                message="Invalid email address",
                user_message="Please provide a valid email address."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResetPasswordResponseSchema:
        """Generate and return password reset token"""
        reset_request = UserResetPasswordRequestInputSchema(**input_data)
        
        # 1. Check if user exists
        user_entity = await self.user_repository.get_by_email(reset_request.email)
        
        if not user_entity:
            # For security, don't reveal if user doesn't exist
            logger.info(f"Password reset requested for non-existent email: {reset_request.email}")
            return UserResetPasswordResponseSchema(
                success=True,  # Return success even if email doesn't exist (security)
                message="If your email exists in our system, you will receive reset instructions.",
                email=reset_request.email
            )
        
        # 2. Check if account is active
        if hasattr(user_entity, 'is_active') and not user_entity.is_active:
            raise DomainValidationException(
                message="Account is not active",
                user_message="Your account is not active. Please contact support."
            )
        
        # 3. Generate reset token
        reset_token = await self.jwt_service.generate_reset_token(
            user_id=user_entity.id,
            email=user_entity.email
        )
        
        # 4. In a real application, send email with reset link
        # For now, we'll just log and return the token (for development/testing)
        reset_link = f"/reset-password?token={reset_token}"
        logger.info(f"Password reset token for {user_entity.email}: {reset_link}")
        
        # 5. Optional: Implement rate limiting or cooldown period
        
        return UserResetPasswordResponseSchema(
            success=True,
            message="Password reset instructions sent to your email",
            email=user_entity.email,
            reset_token=reset_token  # Only for development/testing
        )


class ResetPasswordUseCase(BaseUseCase):
    """Reset password using reset token"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.jwt_service = dependencies.get('jwt_service', JWTAuthService())
        self.password_service = dependencies.get('password_service', PasswordService())
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public endpoint
        self.config.validate_input = True
        self.config.transactional = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate reset password input"""
        try:
            UserResetPasswordInputSchema(**input_data)
        except Exception as e:
            logger.error(f"Reset password validation failed: {str(e)}")
            raise DomainValidationException(
                message="Invalid reset data",
                user_message="Please check your reset data and try again."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> Dict[str, Any]:
        """Reset password using token"""
        reset_input = UserResetPasswordInputSchema(**input_data)
        
        # 1. Verify reset token
        token_data = await self.jwt_service.verify_reset_token(reset_input.token)
        
        if not token_data:
            raise DomainValidationException(
                message="Invalid or expired reset token",
                user_message="The reset link is invalid or has expired. Please request a new one."
            )
        
        # 2. Get user
        user_entity = await self.user_repository.get_by_id(token_data['user_id'])
        
        if not user_entity:
            raise UserNotFoundException(
                user_id=token_data['user_id'],
                user_message="User not found."
            )
        
        # 3. Check password strength
        is_strong, error_message = self.password_service.is_password_strong(reset_input.new_password)
        
        if not is_strong:
            raise DomainValidationException(
                message="Weak password",
                user_message=f"Password is too weak: {error_message}"
            )
        
        # 4. Hash new password
        hashed_password = await self.password_service.hash_password(reset_input.new_password)
        
        # 5. Update user password
        updated_user = await self.user_repository.update(token_data['user_id'], {
            'password': hashed_password,
            'requires_password_change': False,  # Reset the flag if it was set
            'last_password_change': datetime.utcnow()
        })
        
        if not updated_user:
            raise DomainException(
                message="Failed to reset password",
                user_message="Unable to reset password. Please try again."
            )
        
        # 6. Invalidate the reset token
        await self.jwt_service.invalidate_reset_token(token_data['user_id'])
        
        # 7. Optional: Invalidate all existing sessions/tokens for security
        await self.jwt_service.blacklist_all_user_tokens(token_data['user_id'])
        
        # 8. Log the password reset
        logger.info(f"Password reset successful for user ID: {token_data['user_id']}")
        
        return {
            'success': True,
            'message': 'Password reset successfully',
            'user_id': token_data['user_id']
        }


class ChangePasswordUseCase(BaseUseCase):
    """Change password while logged in"""
    
    def __init__(self, user_repository, **dependencies):
        super().__init__(user_repository=user_repository, **dependencies)
        self.user_repository = user_repository
        self.password_service = dependencies.get('password_service', PasswordService())
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True
        self.config.transactional = True
        self.config.audit_log = True
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate change password input"""
        try:
            UserChangePasswordInputSchema(**input_data)
        except Exception as e:
            logger.error(f"Change password validation failed: {str(e)}")
            raise DomainValidationException(
                message="Invalid password change data",
                user_message="Please check your input and try again."
            )
    
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserPasswordChangeResponseSchema:
        """Change password for authenticated user"""
        password_input = UserChangePasswordInputSchema(**input_data)
        
        # 1. Get user with password hash
        user_entity = await self.user_repository.get_by_id(
            password_input.user_id,
            include_password_hash=True
        )
        
        if not user_entity or not hasattr(user_entity, 'password_hash'):
            raise UserNotFoundException(
                user_id=password_input.user_id,
                user_message="User not found."
            )
        
        # 2. Business rule: User can only change their own password unless admin
        if user and hasattr(user, 'id') and user.id != password_input.user_id:
            if not hasattr(user, 'is_superuser') or not user.is_superuser:
                raise DomainValidationException(
                    message="Cannot change another user's password",
                    user_message="You can only change your own password."
                )
        
        # 3. Verify current password
        password_valid = await self.password_service.verify_password(
            password_input.current_password,
            user_entity.password_hash
        )
        
        if not password_valid:
            raise DomainValidationException(
                message="Current password is incorrect",
                user_message="The current password you entered is incorrect."
            )
        
        # 4. Check new password strength
        is_strong, error_message = self.password_service.is_password_strong(password_input.new_password)
        
        if not is_strong:
            raise DomainValidationException(
                message="Weak password",
                user_message=f"New password is too weak: {error_message}"
            )
        
        # 5. Hash new password
        hashed_password = await self.password_service.hash_password(password_input.new_password)
        
        # 6. Update password
        updated_user = await self.user_repository.update(password_input.user_id, {
            'password': hashed_password,
            'last_password_change': datetime.utcnow()
        })
        
        if not updated_user:
            raise DomainException(
                message="Failed to change password",
                user_message="Unable to change password. Please try again."
            )
        
        return UserPasswordChangeResponseSchema(
            success=True,
            message="Password changed successfully",
            requires_login=True
        )