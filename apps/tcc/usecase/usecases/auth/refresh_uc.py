from datetime import datetime, timedelta
import jwt as pyjwt
from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import RefreshTokenInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import TokenRefreshResponseSchema, TokenResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.core.jwt.jwt_backend import JWTManager
import logging
import time

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
        logger.debug(f"Refresh UC input_data: {data}")
        logger.debug(f"Type of input_data: {type(data)}")
        
        # Ensure data is a dict
        if not isinstance(data, dict):
            logger.error(f"Expected dict but got {type(data)}")
            raise InvalidUserInputException(
                field_errors={"general": ["Invalid request format"]},
                user_message="Invalid request format."
            )
        
        # Validate with Pydantic schema - let the schema handle extraction and validation
        try:
            self.validated_input = RefreshTokenInputSchema.model_validate(data)
            logger.debug(f"Pydantic validation successful. Token length: {len(self.validated_input.refresh_token)}")
            
        except ValidationError as e:
            logger.error(f"Pydantic validation failed: {e.errors()}")
            
            # Format Pydantic errors for user-friendly messages
            field_errors = {}
            for error in e.errors():
                field = str(error['loc'][0]) if error['loc'] else 'general'
                msg = error['msg']
                
                # Customize error messages based on error type
                error_type = error.get('type', '')
                if 'missing' in error_type or 'value_error' in error_type:
                    # Check if it's our custom validation message
                    if 'is required' in msg or 'required' in error_type:
                        msg = "Refresh token is required"
                    elif 'too short' in msg:
                        msg = "Token is too short"
                    elif 'Invalid token format' in msg or 'JWT' in msg:
                        msg = "Invalid token format"
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            # Get user-friendly message
            user_message = "Please provide a valid refresh token."
            if 'refresh_token' in field_errors:
                user_message = field_errors['refresh_token'][0]
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )
        
    async def _on_execute(self, input_data, user, ctx):
        """Generate new access token using refresh token"""
        refresh_token = self.validated_input.refresh_token
        
        logger.info(f"Attempting to refresh token. Token length: {len(refresh_token)}")
        
        # Quick sanity check - the schema should have already validated format
        parts = refresh_token.split('.')
        if len(parts) != 3:
            logger.error(f"Invalid JWT format after validation: expected 3 parts, got {len(parts)}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        # 1. Verify refresh token
        try:
            logger.info("Calling jwt_service.verify_refresh_token...")
            token_payload = await self.jwt_service.verify_refresh_token(refresh_token)
            
            if not token_payload:
                logger.warning("Token verification returned None - invalid or expired")
                raise InvalidUserInputException(
                    field_errors={"refresh_token": ["Invalid or expired refresh token"]},
                    user_message="Invalid or expired refresh token. Please login again."
                )
                
            logger.info(f"Token verification SUCCESS for user: {token_payload.get('email', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Token verification failed with exception: {e}", exc_info=True)
            
            # Provide specific error messages
            error_msg = "Invalid or expired refresh token"
            if "expired" in str(e).lower():
                error_msg = "Refresh token has expired. Please login again."
            elif "audience" in str(e).lower():
                error_msg = "Token validation failed due to audience mismatch."
            elif "issuer" in str(e).lower():
                error_msg = "Token validation failed due to issuer mismatch."
            elif "signature" in str(e).lower():
                error_msg = "Invalid token signature."
            
            raise InvalidUserInputException(
                field_errors={"refresh_token": [error_msg]},
                user_message=error_msg
            )
        
        # 2. Extract user_id from token
        user_id = token_payload.get('sub')
        if not user_id:
            logger.error(f"Token payload missing 'sub' field: {token_payload}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        # Convert to string if needed
        user_id = str(user_id)
        logger.info(f"Extracted user_id from token: {user_id}")
        
        # 3. Check if token is blacklisted
        token_id = token_payload.get('jti')
        if token_id:
            try:
                is_blacklisted = await self.jwt_service.is_token_blacklisted(
                    user_id=user_id,
                    token_id=token_id
                )
                
                if is_blacklisted:
                    logger.warning(f"Token is blacklisted: user_id={user_id}, token_id={token_id}")
                    raise InvalidUserInputException(
                        field_errors={"refresh_token": ["Token has been revoked"]},
                        user_message="Refresh token has been revoked. Please login again."
                    )
            except Exception as e:
                logger.error(f"Error checking token blacklist: {e}")
                # Continue anyway - don't fail refresh if blacklist check fails
        
        # 4. Get user data
        user_entity = await self.user_repository.get_by_id(user_id)
        if not user_entity:
            logger.error(f"User not found for ID: {user_id}")
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # 5. Check account status
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
        
        # 6. Extract user role and permissions
        # Get role - single string expected by JWTBackend
        user_role = getattr(user_entity, 'role', None)
        
        # Fallback logic if no direct role attribute
        if not user_role:
            user_roles = getattr(user_entity, 'roles', [])
            if user_roles:
                if isinstance(user_roles, list):
                    user_role = user_roles[0] if user_roles else 'member'
                else:
                    user_role = str(user_roles)
            else:
                user_role = 'member'
        
        # Ensure role is a string
        user_role = str(user_role)
        
        # Get permission flags with defaults
        is_superuser = getattr(user_entity, 'is_superuser', False)
        is_staff = getattr(user_entity, 'is_staff', False)
        
        logger.info(f"Generating new access token for user: {user_entity.email}, role: {user_role}")
        
        # 7. Generate new access token
        try:
            # Try with all parameters first
            new_access_token = await self.jwt_service.generate_access_token_async(
                user_id=user_id,
                email=user_entity.email,
                role=user_role,
                is_superuser=is_superuser,
                is_staff=is_staff
            )
            
        except TypeError as e:
            logger.warning(f"Token generation with all parameters failed: {e}")
            # Try minimal parameters as fallback
            try:
                new_access_token = await self.jwt_service.generate_access_token_async(
                    user_id=user_id,
                    email=user_entity.email,
                    role=user_role
                )
            except Exception as e2:
                logger.error(f"All token generation attempts failed: {e2}")
                raise InvalidUserInputException(
                    field_errors={"token": ["Failed to generate new access token"]},
                    user_message="Unable to refresh token. Please try logging in again."
                )
        
        logger.info(f"New access token generated successfully for user: {user_entity.email}")
        
        # Create expires_at timestamp (current time + 15 minutes)
        expires_in = 900  # 15 minutes
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        # Create the TokenResponseSchema with all required fields
        token_response = TokenResponseSchema(
            access_token=new_access_token,
            expires_in=expires_in,
            expires_at=expires_at,
            token_type="bearer"
        )
        
        # Then wrap it in TokenRefreshResponseSchema
        return TokenRefreshResponseSchema(
            tokens=token_response
        )