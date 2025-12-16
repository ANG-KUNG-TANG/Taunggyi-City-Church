import asyncio
from typing import Dict, Any
from pydantic import ValidationError
from apps.core.core_exceptions.domain import DomainValidationException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserAlreadyExistsException, UserNotFoundException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase, OperationContext
from apps.core.schemas.input_schemas.users import UserCreateInputSchema
from apps.tcc.usecase.entities.users_entity import UserEntity
from apps.tcc.usecase.usecases.base.email_service import EmailService
from apps.tcc.usecase.usecases.base.password_service import PasswordService
import logging

from apps.tcc.usecase.usecases.base.config import OperationContext

logger = logging.getLogger(__name__)

class CreateUserUseCase(BaseUseCase):
    """Create user - Returns UserEntity"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
        
        # Store additional dependencies
        for key, value in dependencies.items():
            if key != 'user_repository':
                setattr(self, key, value)
        
        # Initialize services only if not already provided via dependencies
        if not hasattr(self, 'password_service'):
            self.password_service = PasswordService()
            logger.debug("Created default PasswordService instance")
        
        if not hasattr(self, 'email_service'):
            self.email_service = EmailService()
            logger.debug("Created default EmailService instance")
    
    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.validate_input = True
        self.config.audit_log = True
        self.config.transactional = True

    async def _validate_input(self, input_data: Dict[str, Any], ctx: OperationContext) -> None:
        """Validate user creation input - raises DomainValidationException or UserAlreadyExistsException"""
        try:
            logger.info(f"Input data received: {list(input_data.keys())}")
            
            # Validate against schema
            validated_input = UserCreateInputSchema(**input_data)
            logger.info(f"Schema validation passed for user: {validated_input.email}")
            
            # Check for duplicate email - IMPORTANT: Don't catch the exception here!
            existing_user = await self.user_repository.get_by_email(validated_input.email)
            if existing_user:
                logger.warning(f"User already exists with email: {validated_input.email}")
                raise UserAlreadyExistsException(email=validated_input.email, details={"email": validated_input.email})
            
            # Validate password complexity
            if hasattr(self, '_validate_password'):
                self._validate_password(validated_input.password)
            else:
                logger.warning("_validate_password method not found, skipping password complexity check")
            
        except ValidationError as e:
            logger.error(f"Schema validation failed with {len(e.errors())} errors:")
            
            # Convert validation errors to field errors
            field_errors = {}
            for error in e.errors():
                field = str(error['loc'][0]) if error['loc'] else "unknown"
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(error['msg'])
            
            raise DomainValidationException(
                message=f"Invalid user data: {e.errors()[0]['msg'] if e.errors() else 'Unknown error'}",
                field_errors=field_errors
            )
        # DO NOT catch UserAlreadyExistsException here - let it bubble up
        except UserAlreadyExistsException as e:
            logger.debug(f"Caught UserAlereadEsxistsExceptions in _validate_input: {e}")
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}", exc_info=True)
            raise DomainValidationException(f"Invalid user data: {str(e)}")
    
    def _validate_password(self, password: str) -> None:
        """Validate password complexity."""
        if len(password) < 8:
            raise DomainValidationException("Password must be at least 8 characters")
        
        # Add more complexity rules if needed
        if not any(char.isdigit() for char in password):
            raise DomainValidationException("Password must contain at least one digit")
        
        if not any(char.isalpha() for char in password):
            raise DomainValidationException("Password must contain at least one letter")
                
    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> UserEntity:
        """Create user with business logic - Returns Entity"""
        
        # 1. Validate input using schema
        create_schema = UserCreateInputSchema(**input_data)
        
        # DEBUG: Log all schema fields
        logger.warning(f"Schema fields: {list(create_schema.__dict__.keys())}")
        
        # 2. Business logic: Hash password
        if not hasattr(self, 'password_service') or not self.password_service:
            logger.error("Password service is not available")
            raise DomainValidationException(
                message="Password service not available",
                user_message="User creation is temporarily unavailable."
            )
        
        try:
            hashed_password = await self.password_service.hash_password(create_schema.password)
            logger.debug(f"Password hashed successfully for {create_schema.email}")
        except Exception as e:
            logger.error(f"Failed to hash password: {e}", exc_info=True)
            raise DomainValidationException(
                message="Failed to process password",
                user_message="Unable to process password. Please try again."
            )
        
        # 3. Create entity with hashed password - EXPLICITLY list only fields that exist in User model
        user_data = {
            'name': create_schema.name,
            'email': create_schema.email,
            'password': hashed_password,
            'phone_number': getattr(create_schema, 'phone_number', None),
            'gender': getattr(create_schema, 'gender', None),
            'marital_status': getattr(create_schema, 'marital_status', None),
            'date_of_birth': getattr(create_schema, 'date_of_birth', None),
            'testimony': getattr(create_schema, 'testimony', None),
            'baptism_date': getattr(create_schema, 'baptism_date', None),
            'membership_date': getattr(create_schema, 'membership_date', None),
            'role': getattr(create_schema, 'role', 'VISITOR'),
            'status': getattr(create_schema, 'status', 'PENDING'),
            'email_notifications': getattr(create_schema, 'email_notifications', True),
            'sms_notifications': getattr(create_schema, 'sms_notifications', False),
            'is_active': True,  # Default for new users
        }
        
        # DEBUG: Log what we're about to send
        logger.warning(f"User data being sent to repo: {list(user_data.keys())}")
        logger.warning(f"User data values: {user_data}")
        
        # 4. Create via repository (returns UserEntity)
        try:
            logger.info(f"Calling repository.create() with data for {create_schema.email}")
            user_entity = await self.user_repository.create(user_data)
            logger.info(f"Repository.create() returned: {user_entity}")
        except Exception as e:
            logger.error(f"Repository failed to create user: {e}", exc_info=True)
            raise
        
        if not user_entity:
            logger.error(f"Repository.create() returned None for {create_schema.email}")
            raise DomainValidationException(
                message="Failed to create user - repository returned None",
                user_message="Unable to create user account. Please try again."
            )
        
        logger.info(f"User created successfully: {user_entity.id} ({user_entity.email})")
        
        # 5. Async side effect: Send welcome email if available
        if hasattr(self, 'email_service') and self.email_service:
            try:
                asyncio.create_task(
                    self._send_welcome_email_async(user_entity.email, user_entity.name)
                )
                logger.debug(f"Welcome email scheduled for {user_entity.email}")
            except Exception as e:
                logger.warning(f"Failed to schedule welcome email: {e}")
        
        # 6. Return UserEntity
        return user_entity
    
    async def _send_welcome_email_async(self, email: str, name: str):
        """Send welcome email in background"""
        try:
            success = await self.email_service.send_welcome_email(email, name)
            if success:
                logger.info(f"Welcome email sent successfully to {email}")
            else:
                logger.warning(f"Failed to send welcome email to {email}")
        except Exception as e:
            logger.error(f"Error sending welcome email to {email}: {e}")


class CreateAdminUserUseCase(CreateUserUseCase):
    """Create admin user - Returns UserEntity with admin permissions"""
    
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