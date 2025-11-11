from typing import Dict, Any
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .base_uc import OperationPortalUseCase
from usecase.exceptions.u_exceptions import (
    UserAuthenticationError,
    InvalidUserInputError,
    UserNotFoundException
)

class LoginUseCase(OperationPortalUseCase):
    """Use case for user authentication"""
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Login doesn't require auth
        self.config.required_permissions = []
        self.config.required_roles = []

    def _validate_input(self, input_data: Dict[str, Any], context):
        email = input_data.get('email')
        password = input_data.get('password')

        if not email or not password:
            raise InvalidUserInputError(details={
                "message": "Email and password are required",
                "fields": ["email", "password"]
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        email = input_data.get('email')
        password = input_data.get('password')

        # Authenticate user using Django's authentication
        user_model = authenticate(username=email, password=password)
        if not user_model:
            raise UserAuthenticationError(details={
                "message": "Invalid email or password"
            })

        if not user_model.is_active:
            raise UserAuthenticationError(details={
                "message": "User account is inactive"
            })

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user_model)
        refresh['email'] = user_model.email
        refresh['role'] = user_model.role

        # Convert to entity for response
        user_entity = self.user_repository._model_to_entity(user_model)

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_entity.get_permissions(),
            'user_info': {
                'id': user_model.id,
                'name': user_model.name,
                'email': user_model.email,
                'role': user_model.role,
                'status': user_model.status
            }
        }

class RefreshTokenUseCase(OperationPortalUseCase):
    """Use case for token refresh"""
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    def _validate_input(self, input_data: Dict[str, Any], context):
        refresh_token = input_data.get('refresh')
        if not refresh_token:
            raise InvalidUserInputError(details={
                "message": "Refresh token is required",
                "field": "refresh"
            })

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        refresh_token = input_data.get('refresh')

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh['user_id']

            # Get user from repository
            user_model = self.user_repository.model_class.objects.get(id=user_id)
            if not user_model.is_active:
                raise UserAuthenticationError(details={
                    "message": "User account is inactive"
                })

            # Generate new tokens
            new_refresh = RefreshToken.for_user(user_model)
            new_refresh['email'] = user_model.email
            new_refresh['role'] = user_model.role

            return {
                'access': str(new_refresh.access_token),
                'refresh': str(new_refresh)
            }

        except self.user_repository.model_class.DoesNotExist:
            raise UserNotFoundException(user_id=user_id)
        except Exception as e:
            raise UserAuthenticationError(details={
                "message": "Invalid or expired refresh token"
            })

class LogoutUseCase(OperationPortalUseCase):
    """Use case for user logout"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        refresh_token = input_data.get('refresh')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                # Ignore blacklist errors
                pass

        return {
            "message": "Successfully logged out",
            "user_id": user.id
        }

class VerifyTokenUseCase(OperationPortalUseCase):
    """Use case for token verification"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        """Verify user token and return user info"""
        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "is_active": user.is_active,
            "permissions": user.get_permissions()
        }