from asyncio.log import logger
from typing import Dict, Any, Optional
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.tcc.usecase.domain_exception.u_exceptions import (
    DomainValidationException, 
    UserAlreadyExistsException
)
from apps.tcc.usecase.usecases.base.config import OperationContext

class RegisterUserUseCase(BaseUseCase):
    """Use case for public user registration (simpler version)"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def _validate_input(self, input_data: Dict[str, Any], ctx: OperationContext) -> None:
        """Simple validation for registration"""
        # Check required fields
        required_fields = ['name', 'email', 'password', 'password_confirm']
        for field in required_fields:
            if field not in input_data:
                raise DomainValidationException(f"Missing required field: {field}")
        
        # Check password match
        if input_data.get('password') != input_data.get('password_confirm'):
            raise DomainValidationException("Passwords do not match")
        
        # Check password length
        if len(input_data.get('password', '')) < 8:
            raise DomainValidationException("Password must be at least 8 characters")
        
        # Check if email exists (simpler approach)
        email = input_data.get('email')
        if email:
            # Direct database query without decorator issues
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                if User.objects.filter(email=email).exists():
                    raise UserAlreadyExistsException(f"Email {email} already exists")
            except Exception as e:
                logger.warning(f"Could not check email existence: {e}")
    
    async def _execute_operation(self, ctx: OperationContext) -> UserEntity:
        """Execute the registration"""
        input_data = ctx.input_data
        
        # Create user data dictionary
        user_data = {
            'name': input_data.get('name'),
            'email': input_data.get('email'),
            'password': input_data.get('password'),
            'is_active': input_data.get('is_active', True)
        }
        
        # Create user
        user = await self.user_repository.create(user_data, ctx.current_user, ctx.context)
        return UserEntity.from_domain(user)