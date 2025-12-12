from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import RefreshTokenInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import TokenRefreshResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.core.jwt.jwt_backend import JWTManager
import logging

logger = logging.getLogger(__name__)


class RefreshTokenUseCase(BaseUseCase):
    """Refresh access token using refresh token"""

    def __init__(self, user_repository: UserRepository, jwt_service: JWTManager):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_service = jwt_service

    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, data, ctx):
        """Validate refresh token input"""
        # Check if we have the basic data structure
        if not data or not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Refresh token is required"]},
                user_message="Please provide a refresh token."
            )
        
        # Check for missing refresh token
        refresh_token = data.get('refresh_token', '').strip()
        if not refresh_token:
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Refresh token is required"]},
                user_message="Refresh token is required."
            )
        
        # Now validate with Pydantic schema
        try:
            self.validated_input = RefreshTokenInputSchema(**data)
        except ValidationError as e:
            # Format Pydantic errors
            field_errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'general'
                msg = error['msg']
                
                # Customize error messages
                error_type = error.get('type', '')
                if error_type == 'value_error.missing':
                    msg = "Refresh token is required"
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            user_message = "Please provide a valid refresh token."
            if 'refresh_token' in field_errors:
                user_message = field_errors['refresh_token'][0]
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )

    async def _on_execute(self, data, user, ctx):
        """Generate new access token using refresh token"""
        refresh_token = self.validated_input.refresh_token
        
        # 1. Verify refresh token
        try:
            token_payload = await self.jwt_service.verify_refresh_token(refresh_token)
            if not token_payload:
                raise InvalidUserInputException(
                    field_errors={"refresh_token": ["Invalid or expired refresh token"]},
                    user_message="Refresh token is invalid or expired."
                )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid refresh token"]},
                user_message="Refresh token is invalid."
            )
        
        user_id = token_payload.get('user_id')
        
        # 2. Check if token is blacklisted
        is_blacklisted = await self.jwt_service.is_token_blacklisted(
            user_id=user_id,
            token_id=token_payload.get('jti')
        )
        
        if is_blacklisted:
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Token has been revoked"]},
                user_message="Refresh token has been revoked. Please login again."
            )
        
        # 3. Get user data
        user_entity = await self.user_repository.get_by_id(user_id)
        if not user_entity:
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # 4. Check account status
        if getattr(user_entity, 'is_locked', False):
            raise InvalidUserInputException(
                field_errors={"account": ["Account is locked"]},
                user_message="Your account is locked. Please contact support."
            )
        
        if not getattr(user_entity, 'is_active', True):
            raise InvalidUserInputException(
                field_errors={"account": ["Account is inactive"]},
                user_message="Your account is inactive."
            )
        
        # 5. Generate new access token
        user_roles = getattr(user_entity, 'roles', [])
        if not user_roles and hasattr(user_entity, 'role'):
            user_roles = [user_entity.role]
        
        new_access_token = await self.jwt_service.generate_access_token(
            user_id=user_entity.id,
            email=user_entity.email,
            roles=user_roles
        )
        
        return TokenRefreshResponseSchema(
            access_token=new_access_token,
            expires_in=900,  # 15 minutes
            token_type="bearer"
        )