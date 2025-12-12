import asyncio
from typing import Dict, Any
from pydantic import ValidationError
from apps.core.schemas.input_schemas.auth import LogoutInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import LogoutResponseSchema
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.jwt.jwt_backend import JWTManager
import logging

logger = logging.getLogger(__name__)


class LogoutUseCase(BaseUseCase):
    """User logout use case - handles token revocation and audit logging"""

    def __init__(self, auth_service: AsyncAuthDomainService, jwt_service: JWTManager):
        super().__init__()
        self.auth_service = auth_service
        self.jwt_service = jwt_service

    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.audit_log = True

    async def _validate_input(self, data, ctx):
        """Validate input using LogoutInputSchema"""
        # Logout can accept empty data (just logging out without token revocation)
        # But if data is provided, validate it
        if data is not None and not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Invalid logout request format"]},
                user_message="Invalid logout request."
            )
        
        # If no data provided, use empty dict
        if data is None:
            data = {}
        
        try:
            self.validated_input = LogoutInputSchema(**data)
        except ValidationError as e:
            # Format Pydantic errors
            field_errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'general'
                msg = error['msg']
                
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
            
            user_message = "Invalid logout request"
            if 'refresh_token' in field_errors:
                user_message = "Invalid refresh token format"
            
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message=user_message
            )

    async def _on_execute(self, data, user, ctx):
        """Execute logout business logic"""
        token_str = self.validated_input.refresh_token
        request_meta = ctx.get('request_meta', {}) if ctx else {}
        
        # Business Rule: Token revocation (if provided)
        if token_str:
            # Verify token belongs to user before revoking
            try:
                token_payload = await self.jwt_service.verify_token(token_str)
                if token_payload.get('user_id') == user.id:
                    # Revoke token asynchronously
                    asyncio.create_task(
                        self.auth_service.revoke_token_async(token_str, user.id)
                    )
            except Exception as e:
                # Log but don't fail logout if token verification fails
                logger.warning(f"Token verification failed during logout for user {user.id}: {e}")
        
        # Business Rule: Audit logging
        asyncio.create_task(
            self.auth_service.audit_login_async(user.id, "LOGOUT", request_meta)
        )
        
        # Return domain schema
        return LogoutResponseSchema(
            message="Logout successful",
            user_id=user.id,
            timestamp=asyncio.get_event_loop().time()
        )