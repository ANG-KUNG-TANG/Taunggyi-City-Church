from typing import Dict, Any, Optional
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import VerifyTokenInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import AuthSuccessResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.core.jwt.jwt_backend import JWTBackend, TokenType
import logging

logger = logging.getLogger(__name__)


class VerifyTokenUseCase(BaseUseCase):
    """Verify token and user status - supports both header and body tokens"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_backend = JWTBackend.get_instance()

    def _setup_configuration(self):
        self.config.require_authentication = False  # We handle token verification ourselves

    async def _validate_input(self, data, ctx):
        """Validate input if provided"""
        # Token can come from Authorization header OR request body
        # If data is provided, validate it with schema
        if data is not None and isinstance(data, dict) and data:
            try:
                # Use the schema to validate and extract token
                self.validated_input = VerifyTokenInputSchema.model_validate(data)
                logger.debug("Token validated from request body")
            except ValidationError as e:
                logger.error(f"Token validation failed: {e.errors()}")
                # Don't raise error here - token might be in header
                self.validated_input = None
        else:
            self.validated_input = None
        
        # No error if no token in body - it might be in header

    async def _on_execute(self, data, user, ctx):
        """Verify user and token status"""
        # Priority 1: Check if we have a token from request body
        if hasattr(self, 'validated_input') and self.validated_input and self.validated_input.token:
            token = self.validated_input.token
            logger.info(f"Verifying token from request body: {token[:30]}...")
            return await self._verify_token_from_body(token)
        
        # Priority 2: Check if we have a user from authentication middleware (token in header)
        if user:
            logger.info(f"Verifying user from auth middleware: {user.email}")
            return await self._verify_user_from_auth(user)
        
        # No token found anywhere
        raise InvalidUserInputException(
            field_errors={"token": ["Token is required"]},
            user_message="Authentication required. Please provide a token in Authorization header or request body."
        )
    
    async def _verify_token_from_body(self, token: str) -> AuthSuccessResponseSchema:
        """Verify token from request body"""
        # Verify the token using JWT backend
        is_valid, payload = await self.jwt_backend.verify_token(token, TokenType.ACCESS)
        
        if not is_valid or not payload:
            logger.warning(f"Token verification failed for token: {token[:50]}...")
            # Check if the token is a refresh token
            is_refresh_valid, refresh_payload = await self.jwt_backend.verify_token(token, TokenType.REFRESH)
            if is_refresh_valid and refresh_payload:
                raise InvalidUserInputException(
                    field_errors={"token": ["Token is a refresh token, not an access token"]},
                    user_message="Please provide an access token, not a refresh token."
                )
            else:
                raise InvalidUserInputException(
                    field_errors={"token": ["Invalid or expired token"]},
                    user_message="Invalid or expired token."
                )
        
        # Extract user_id from token
        user_id = payload.get('sub')
        if not user_id:
            logger.error(f"Token payload missing 'sub' field: {payload}")
            raise InvalidUserInputException(
                field_errors={"token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        # Get fresh user data
        user_entity = await self.user_repository.get_by_id(str(user_id))
        
        if not user_entity:
            logger.error(f"User not found for ID: {user_id}")
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # Check account status
        if getattr(user_entity, 'is_locked', False):
            logger.warning(f"User account is locked: {user_id}")
            raise InvalidUserInputException(
                field_errors={"account": ["Account is locked"]},
                user_message="Your account is locked. Please contact support."
            )
        
        if not getattr(user_entity, 'is_active', True):
            logger.warning(f"User account is inactive: {user_id}")
            raise InvalidUserInputException(
                field_errors={"account": ["Account is inactive"]},
                user_message="Your account is inactive."
            )
        
        # Return verification result
        return AuthSuccessResponseSchema(
            success=True,
            message="Token is valid",
            user_id=user_entity.id,
            email=user_entity.email,
            is_active=True,
            requires_password_change=getattr(user_entity, 'requires_password_change', False)
        )
    
    async def _verify_user_from_auth(self, user) -> AuthSuccessResponseSchema:
        """Verify user from auth middleware"""
        # Get fresh user data
        user_entity = await self.user_repository.get_by_id(user.id)
        
        if not user_entity:
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # Check account status
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
        
        # Return verification result
        return AuthSuccessResponseSchema(
            success=True,
            message="Token is valid",
            user_id=user_entity.id,
            email=user_entity.email,
            is_active=True,
            requires_password_change=getattr(user_entity, 'requires_password_change', False)
        )