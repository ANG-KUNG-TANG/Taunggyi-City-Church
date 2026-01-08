from datetime import datetime
import jwt as pyjwt
from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.input_schemas.auth import RefreshTokenInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import TokenRefreshResponseSchema
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
        
        # Extract refresh token from various possible field names
        refresh_token = (
            data.get('refresh_token') or 
            data.get('refresh') or 
            data.get('refreshToken')
        )
        
        logger.debug(f"Extracted refresh_token: {refresh_token[:30] if refresh_token else 'None'}...")
        
        # Check if token exists
        if not refresh_token:
            logger.error(f"Refresh token missing. Available keys: {list(data.keys())}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Refresh token is required"]},
                user_message="Refresh token is required."
            )
        
        # Ensure it's a string and clean it
        refresh_token = str(refresh_token).strip()
        
        if not refresh_token:
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Refresh token cannot be empty"]},
                user_message="Refresh token cannot be empty."
            )
        
        # Normalize the data to use 'refresh_token' as the key
        normalized_data = {'refresh_token': refresh_token}
        
        # Validate with Pydantic schema
        try:
            self.validated_input = RefreshTokenInputSchema(**normalized_data)
            logger.debug("Pydantic validation successful")
        except ValidationError as e:
            logger.error(f"Pydantic validation failed: {e.errors()}")
            
            # Format Pydantic errors for user-friendly messages
            field_errors = {}
            for error in e.errors():
                field = str(error['loc'][0]) if error['loc'] else 'general'
                msg = error['msg']
                
                # Customize error messages based on error type
                error_type = error.get('type', '')
                if 'missing' in error_type:
                    msg = "Refresh token is required"
                elif 'string' in error_type:
                    msg = "Refresh token must be a valid string"
                
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
        logger.info(f"Refresh token (first 100 chars): {refresh_token[:100]}...")
        
        # Check JWT format
        parts = refresh_token.split('.')
        if len(parts) != 3:
            logger.error(f"Invalid JWT format: expected 3 parts, got {len(parts)}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        logger.info(f"JWT format valid: header={parts[0][:20]}..., payload={parts[1][:20]}..., signature={parts[2][:20]}...")
        
        # First, try to decode without verification to see what's in the token
        try:
            unverified_payload = pyjwt.decode(
                refresh_token, 
                options={"verify_signature": False}
            )
            logger.info(f"Token decoded (without verification):")
            logger.info(f"  - token_type: {unverified_payload.get('token_type')}")
            logger.info(f"  - sub: {unverified_payload.get('sub')}")
            logger.info(f"  - email: {unverified_payload.get('email')}")
            logger.info(f"  - iss: {unverified_payload.get('iss')}")
            logger.info(f"  - aud: {unverified_payload.get('aud')}")
            logger.info(f"  - jti: {unverified_payload.get('jti')}")
            logger.info(f"  - iat: {unverified_payload.get('iat')} ({datetime.fromtimestamp(unverified_payload.get('iat')).isoformat() if unverified_payload.get('iat') else 'N/A'})")
            logger.info(f"  - exp: {unverified_payload.get('exp')} ({datetime.fromtimestamp(unverified_payload.get('exp')).isoformat() if unverified_payload.get('exp') else 'N/A'})")
            
            # Check expiration
            if unverified_payload.get('exp'):
                current_time = time.time()
                exp_time = unverified_payload.get('exp')
                if exp_time < current_time:
                    logger.warning(f"Token expired! exp={exp_time}, current={current_time}")
                    raise InvalidUserInputException(
                        field_errors={"refresh_token": ["Refresh token has expired"]},
                        user_message="Refresh token has expired. Please login again."
                    )
            
        except Exception as decode_error:
            logger.error(f"Cannot decode token even without verification: {decode_error}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        # 1. Verify refresh token
        try:
            logger.info("Calling jwt_service.verify_refresh_token...")
            token_payload = await self.jwt_service.verify_refresh_token(refresh_token)
            logger.info(f"Token verification result type: {type(token_payload)}")
            
            if token_payload:
                logger.info(f"Token verification SUCCESS!")
                logger.info(f"Token payload keys: {list(token_payload.keys())}")
                logger.info(f"Token user (sub): {token_payload.get('sub')}")
                logger.info(f"Token type: {token_payload.get('token_type')}")
            else:
                logger.warning("Token verification returned None!")
                
                # Try to understand why verification failed
                # Check if it's an audience issue
                if 'aud' in unverified_payload:
                    logger.info(f"Token audience: {unverified_payload.get('aud')}")
                    logger.info(f"Expected audience from config: This should match what's in JWT config")
                
                # Check if it's a token type issue
                token_type = unverified_payload.get('token_type')
                if token_type != 'refresh':
                    logger.error(f"Wrong token type! Expected 'refresh', got '{token_type}'")
                    raise InvalidUserInputException(
                        field_errors={"refresh_token": ["Not a refresh token"]},
                        user_message="This is not a refresh token. Please provide a valid refresh token."
                    )
                
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
        
        # 2. Check if token payload is valid
        if not token_payload:
            logger.warning("Token verification returned None. Token might be invalid or expired.")
            
            # Try to manually verify to get specific error
            try:
                # This will raise a specific exception
                from apps.core.jwt.jwt_backend import TokenType
                is_valid, payload = self.jwt_service.verify_token_sync(
                    refresh_token, 
                    token_type=TokenType.REFRESH
                )
                if not is_valid:
                    logger.error("Manual verification also failed!")
            except Exception as manual_error:
                logger.error(f"Manual verification error: {manual_error}")
            
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid or expired refresh token"]},
                user_message="Invalid or expired refresh token."
            )
        
        # 3. Extract user_id from token
        user_id = token_payload.get('sub')
        if not user_id:
            logger.error(f"Token payload missing 'sub' field: {token_payload}")
            raise InvalidUserInputException(
                field_errors={"refresh_token": ["Invalid token format"]},
                user_message="Invalid token format."
            )
        
        logger.info(f"Extracted user_id from token: {user_id}")
        
        # 4. Check if token is blacklisted
        token_id = token_payload.get('jti')
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
        
        # 5. Get user data
        user_entity = await self.user_repository.get_by_id(user_id)
        if not user_entity:
            logger.error(f"User not found for ID: {user_id}")
            raise InvalidUserInputException(
                field_errors={"user": ["User not found"]},
                user_message="User account not found."
            )
        
        # 6. Check account status
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
        
        # 7. Generate new access token
        user_roles = getattr(user_entity, 'roles', [])
        if not user_roles and hasattr(user_entity, 'role'):
            user_roles = [user_entity.role]
        
        logger.info(f"Generating new access token for user: {user_id}, email: {user_entity.email}")
        
        new_access_token = await self.jwt_service.generate_access_token_async(
            user_id=user_id,
            email=user_entity.email,
            roles=user_roles
        )
        
        logger.info(f"New access token generated successfully for user: {user_entity.email}")
        
        return TokenRefreshResponseSchema(
            access_token=new_access_token,
            expires_in=900,  # 15 minutes
            token_type="bearer"
        )