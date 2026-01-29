import asyncio
from typing import Dict, Any
from apps.core.core_exceptions.domain import DomainException, DomainValidationException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.core.schemas.input_schemas.users import UserUpdateInputSchema
import logging

logger = logging.getLogger(__name__)


class UpdateUserUseCase(BaseUseCase):
    """Update user - Returns UserEntity"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
        # Store additional dependencies
        for key, value in dependencies.items():
            if key != 'user_repository':
                setattr(self, key, value)
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.validate_input = True
        self.config.audit_log = True
        self.config.transactional = True

    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Validate update input with business rules"""
        user_id = input_data.get('user_id')
        update_data = input_data.get('update_data', {})
        
        if not user_id:
            raise DomainValidationException("User ID is required.")
        
        if not update_data:
            raise DomainValidationException("Update data is required.")
        
        try:
            # Convert user_id to integer
            user_id = int(user_id)
            
            # Validate update schema
            UserUpdateInputSchema(**update_data)
            
            # Business rule: User can only update their own profile unless admin
            if not await self._can_update_user(ctx.user, user_id):
                raise DomainValidationException(
                    "You can only update your own profile",
                    user_message="You do not have permission to update this user."
                )
                
        except ValueError:
            raise DomainValidationException("Invalid User ID format.")
        except Exception as e:
            logger.error(f"Update validation failed: {str(e)}")
            raise

    async def _can_update_user(self, current_user, target_user_id: int) -> bool:
        """Business rule: Check if user can update target user"""
        if not current_user:
            return False
            
        # Admin can update anyone
        if hasattr(current_user, 'is_superuser') and current_user.is_superuser:
            return True
            
        # User can update their own profile
        if hasattr(current_user, 'id') and current_user.id == target_user_id:
            return True
            
        return False

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx):
        """Update user with business logic - Returns UserEntity"""
        user_id = int(input_data['user_id'])
        update_data = input_data.get('update_data', {})
        
        # 1. Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id, user=user)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # 2. Business rule: Prevent email change without verification
        if 'email' in update_data and update_data['email'] != existing_user.email:
            if not hasattr(self, 'email_verification_service') or not self.email_verification_service:
                # Remove email from update for now
                logger.warning(f"Email change requested for user {user_id} but no verification service available")
                del update_data['email']
            else:
                # Send verification email
                await self.email_verification_service.send_email_change_verification(
                    user_id=user_id,
                    old_email=existing_user.email,
                    new_email=update_data['email']
                )
                logger.info(f"Email verification sent for user {user_id}")
        
        # 3. Prepare context for audit (if needed)
        request = None
        if hasattr(ctx, 'request'):
            request = ctx.request
        elif isinstance(ctx, dict) and 'request' in ctx:
            request = ctx['request']
        
        # 4. Update via repository
        updated_entity = await self.user_repository.update(
            object_id=user_id,
            data=update_data,
            user=user,
            request=request
        )
        
        if not updated_entity:
            raise DomainException(
                "Failed to update user",
                user_message="Unable to update user profile. Please try again."
            )
        
        # 5. Async side effect: Log update
        if hasattr(self, 'audit_service') and self.audit_service:
            asyncio.create_task(
                self.audit_service.log_user_update(
                    user_id=user_id,
                    updated_by=user.id if user else None,
                    changes=update_data
                )
            )
        
        return updated_entity


class ChangeUserStatusUseCase(BaseUseCase):
    """Change user status - Returns UserEntity"""
    
    def __init__(self, user_repository: UserRepository, **dependencies):
        super().__init__(**dependencies)
        self.user_repository = user_repository
        # Store additional dependencies
        for key, value in dependencies.items():
            if key != 'user_repository':
                setattr(self, key, value)
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_users']
        self.config.validate_input = True
        self.config.audit_log = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx):
        """Change status with business rules - Returns UserEntity"""
        user_id = int(input_data['user_id'])
        new_status = input_data['status']
        
        # 1. Check if user exists
        target_user = await self.user_repository.get_by_id(user_id, user=user)
        if not target_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # 2. Business rule: Cannot deactivate self
        if user and user.id == user_id and new_status == 'inactive':
            raise DomainValidationException(
                "Cannot deactivate your own account",
                user_message="You cannot deactivate your own account."
            )
        
        # 3. Business rule: Cannot change status of super admin
        if target_user and hasattr(target_user, 'is_superuser') and target_user.is_superuser:
            if user and not hasattr(user, 'is_superuser') or not user.is_superuser:
                raise DomainValidationException(
                    "Cannot change status of super admin",
                    user_message="You do not have permission to modify super admin accounts."
                )
        
        # 4. Prepare context for audit
        request = None
        if hasattr(ctx, 'request'):
            request = ctx.request
        elif isinstance(ctx, dict) and 'request' in ctx:
            request = ctx['request']
        
        # 5. Update status
        status_update_data = {'status': new_status}
        updated_entity = await self.user_repository.update(
            object_id=user_id,
            data=status_update_data,
            user=user,
            request=request
        )
        
        if not updated_entity:
            raise DomainException("Failed to change user status")
        
        # 6. Async: Log status change
        if hasattr(self, 'notification_service') and self.notification_service:
            asyncio.create_task(
                self.notification_service.notify_status_change(
                    user_id=user_id,
                    old_status=getattr(target_user, 'status', 'active'),
                    new_status=new_status
                )
            )
        
        return updated_entity