import asyncio
from typing import Dict, Any
from apps.core.core_exceptions.domain import DomainValidationException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.schemas.input_schemas.users import UserCreateInputSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.usecases.base.password_service import PasswordService
from apps.tcc.usecase.usecases.base.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

class CreateUserUseCase(BaseUseCase):
    """Create user - Returns UserResponseSchema"""
    
    def __init__(self, user_repository: UserRepository = None, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository or UserRepository()
        # Inject services if provided
        self.password_service = dependencies.get('password_service') or PasswordService()
        self.email_service = dependencies.get('email_service')
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Allow registration without auth
        self.config.validate_input = True
        self.config.audit_log = True
        self.config.transactional = True

    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Business rule validation"""
        try:
            # Use input schema for validation
            validated_input = UserCreateInputSchema(**input_data)
            
            # Check email uniqueness (business rule)
            if await self.user_repository.email_exists(validated_input.email):
                raise UserAlreadyExistsException(
                    email=validated_input.email,
                    user_message="Email already exists. Please use a different email or login."
                )
                
            # Check password strength if password service is available
            if self.password_service and not await self.password_service.is_password_strong(validated_input.password):
                raise DomainValidationException(
                    message="Password is too weak",
                    user_message="Password must be at least 8 characters with uppercase, lowercase, and numbers."
                )
                
        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            if isinstance(e, UserAlreadyExistsException):
                raise
            # Re-raise DomainValidationException as is
            if isinstance(e, DomainValidationException):
                raise
            raise DomainValidationException(
                message="Invalid user data",
                details={"errors": str(e)},
                user_message="Please check your input data and try again."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserResponseSchema:
        """Create user with business logic - Returns Schema"""
        
        # 1. Validate input using schema
        create_schema = UserCreateInputSchema(**input_data)
        
        # 2. Business logic: Hash password (require password service)
        if not self.password_service:
            raise DomainValidationException(
                message="Password service not available",
                user_message="User creation is temporarily unavailable."
            )
        
        hashed_password = await self.password_service.hash_password(create_schema.password)
        
        # 3. Create entity with hashed password
        user_data = create_schema.model_dump(exclude={'password', 'password_confirm'})
        user_data['password'] = hashed_password  # Store as 'password' field
        
        # 4. Add audit context
        user_data_with_context = self._add_audit_context(user_data, user, ctx)
        
        # 5. Create via repository (returns UserEntity)
        user_entity = await self.user_repository.create(user_data_with_context)
        
        if not user_entity:
            raise DomainValidationException(
                message="Failed to create user",
                user_message="Unable to create user account. Please try again."
            )
        
        # 6. Async side effect: Send welcome email if email service is available
        if self.email_service:
            asyncio.create_task(
                self.email_service.send_welcome_email(user_entity.email, user_entity.name)
            )
        
        # 7. Return response schema (Domain Schema)
        return UserResponseSchema.model_validate(user_entity)


class CreateAdminUserUseCase(CreateUserUseCase):
    """Create admin user - Returns UserResponseSchema with admin permissions"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.required_roles = ['admin', 'super_admin']
        self.config.validate_input = True
        self.config.audit_log = True
        self.config.transactional = True

    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        await super()._validate_input(input_data, ctx)
        
        # Additional business rule: Admin creation requires special authorization
        if not ctx.user or not hasattr(ctx.user, 'is_superuser'):
            raise DomainValidationException(
                message="Unauthorized to create admin users",
                user_message="You do not have permission to create admin users."
            )


