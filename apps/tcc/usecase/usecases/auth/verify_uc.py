from typing import Dict, Any
from pydantic import ValidationError

from apps.core.schemas.out_schemas.aut_out_schemas import AuthSuccessResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
import logging

logger = logging.getLogger(__name__)


class VerifyTokenUseCase(BaseUseCase):
    """Verify token and user status"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, data, ctx):
        """Validate input if provided (can be empty for token verification)"""
        # Token verification usually doesn't require input data
        # But if data is provided, ensure it's a valid dict
        if data is not None and not isinstance(data, dict):
            raise InvalidUserInputException(
                field_errors={"general": ["Invalid input format"]},
                user_message="Invalid request."
            )
        
        # If data is provided, you could validate it here
        # For now, we just accept any data or none

    async def _on_execute(self, data, user, ctx):
        """Verify user and token status"""
        if not user:
            raise InvalidUserInputException(
                field_errors={"token": ["Invalid or missing token"]},
                user_message="Authentication required."
            )
        
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