from typing import Dict, Any, List
from apps.core.schemas.builders.user_rp_builder import UserResponseBuilder
from apps.core.schemas.common.response import UserRegistrationResponse, APIResponse
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.base.jwt_uc import JWTCreateUseCase
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import (
    InvalidUserInputException, 
    UserAlreadyExistsException
)
from apps.tcc.usecase.entities.users import UserEntity
from apps.core.schemas.schemas.users import UserCreateSchema


class CreateUserUseCase(BaseUseCase):
    """Fixed user creation use case"""
    
    def __init__(self, user_repository: UserRepository, jwt_uc: JWTCreateUseCase):
        super().__init__()
        self.user_repository = user_repository
        self.jwt_uc = jwt_uc
    
    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.required_permissions = []

    async def _validate_input(self, input_data: Dict[str, Any], context):
        # Validate using Pydantic schema
        try:
            validated_data = UserCreateSchema(**input_data)
        except Exception as e:
            field_errors = self._extract_pydantic_errors(e)
            raise InvalidUserInputException(
                field_errors=field_errors,
                user_message="Please check your input data and try again."
            )

        # Check email uniqueness
        if await self.user_repository.email_exists(validated_data.email):
            raise UserAlreadyExistsException(
                email=validated_data.email,
                user_message="An account with this email already exists."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> UserRegistrationResponse:
        # Extract password before creating entity
        password = input_data.get('password')
        
        # Create entity using proper constructor
        user_entity = UserEntity.from_create_schema(UserCreateSchema(**input_data))
        
        # Validate entity business rules
        validation_errors = user_entity.validate_for_creation()
        if validation_errors:
            raise InvalidUserInputException(
                field_errors={"_form": validation_errors},
                user_message="Please check your input data."
            )
        
        # Create user with password
        created_user = await self.user_repository.create(user_entity, password)

        # Generate tokens
        tokens = await self.jwt_uc.execute(
            user_id=str(created_user.id),
            email=created_user.email,
            roles=[created_user.role]
        )

        # Build response
        user_response = UserResponseBuilder.to_response(created_user)
        
        return UserRegistrationResponse.from_user_and_tokens(
            user_data=user_response.model_dump(),
            tokens_data=tokens,
            message="User created successfully"
        )

    def _extract_pydantic_errors(self, validation_error: Exception) -> Dict[str, List[str]]:
        """Extract field errors from Pydantic validation"""
        field_errors = {}
        if hasattr(validation_error, 'errors'):
            for error in validation_error.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                field_errors.setdefault(field, []).append(error['msg'])
        else:
            field_errors['_form'] = [str(validation_error)]
        return field_errors