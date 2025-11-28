from typing import Dict, Any
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.usecase.entities.users import UserEntity
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository

class UpdateUserUseCase(BaseUseCase):
    """Update user - assumes data is pre-validated"""
    
    def __init__(self, user_repository:UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Any:
        user_id = int(input_data['user_id'])
        update_data = input_data.get('update_data', {})
        
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(user_id=user_id, user_message="User not found.")
        
        # Add audit context to update data
        update_data_with_context = update_data.copy()
        update_data_with_context['user'] = user
        if context and hasattr(context, 'request'):
            request = context.request
            update_data_with_context['ip_address'] = self._get_client_ip(request)
            update_data_with_context['user_agent'] = request.META.get('HTTP_USER_AGENT', 'system')
        
        # Update user using repository
        updated_user = await self.user_repository.update(user_id, update_data_with_context)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id, user_message="Failed to update user.")
        
        return updated_user
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ChangeUserStatusUseCase(BaseUseCase):
    """Change user status - assumes data is pre-validated"""
    
    def __init__(self, user_repository):
        super().__init__()
        self.user_repository = user_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Any:
        user_id = int(input_data['user_id'])
        new_status = input_data.get('status')
        
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(user_id=user_id, user_message="User not found.")
        
        # Prepare update data with audit context
        update_data = {'status': new_status}
        update_data['user'] = user
        if context and hasattr(context, 'request'):
            request = context.request
            update_data['ip_address'] = self._get_client_ip(request)
            update_data['user_agent'] = request.META.get('HTTP_USER_AGENT', 'system')
        
        updated_user = await self.user_repository.update(user_id, update_data)
        
        if not updated_user:
            raise UserNotFoundException(user_id=user_id, user_message="Failed to change user status.")
        
        return updated_user
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip