import asyncio
from typing import Dict, Any
from apps.core.core_exceptions.domain import DomainException, DomainValidationException
from apps.core.schemas.out_schemas.base import DeleteResponseSchema
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
import logging

logger = logging.getLogger(__name__)


class DeleteUserUseCase(BaseUseCase):
    """Soft delete user - Returns boolean"""
    
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
        self.config.transactional = True

    async def _validate_input(self, input_data: Dict[str, Any], ctx):
        """Business rule validation for deletion"""
        user_id = input_data.get('user_id')
        
        if not user_id:
            raise DomainValidationException("User ID is required.")
        
        # Business rule: Cannot delete self
        if ctx.user and ctx.user.id == int(user_id):
            raise DomainValidationException(
                "Cannot delete your own account",
                user_message="You cannot delete your own account."
            )
        
        # Business rule: Cannot delete super admin unless you're super admin
        target_user = await self.user_repository.get_by_id(int(user_id))
        if target_user and hasattr(target_user, 'is_superuser') and target_user.is_superuser:
            if not ctx.user or not hasattr(ctx.user, 'is_superuser') or not ctx.user.is_superuser:
                raise DomainValidationException(
                    "Cannot delete super admin account",
                    user_message="You do not have permission to delete super admin accounts."
                )

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> bool:
        """Delete user with business logic - Returns boolean success"""
        user_id = int(input_data['user_id'])
        
        # 1. Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundException(
                user_id=user_id,
                user_message="User not found."
            )
        
        # 2. Business rule: Check for active dependencies
        if hasattr(self, 'dependency_checker') and self.dependency_checker:
            has_dependencies = await self.dependency_checker.check_user_dependencies(user_id)
            if has_dependencies:
                raise DomainValidationException(
                    "User has active dependencies",
                    user_message="Cannot delete user because they have active records. Please transfer or archive them first."
                )
        
        # 3. Soft delete via repository
        success = await self.user_repository.delete(user_id, user, ctx)
        
        if not success:
            raise DomainException(
                "Failed to delete user",
                user_message="Unable to delete user. Please try again."
            )
        
        # 4. Async side effects
        if hasattr(self, 'notification_service') and self.notification_service:
            asyncio.create_task(
                self.notification_service.notify_user_deletion(
                    user_id=user_id,
                    deleted_by=user.id if user else None
                )
            )
        
        # 5. Return boolean success
        return success


class BulkDeleteUsersUseCase(BaseUseCase):
    """Bulk delete users - Returns DeleteResponseSchema"""
    
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
        self.config.transactional = True

    async def _on_execute(self, input_data: Dict[str, Any], user, ctx) -> DeleteResponseSchema:
        """Bulk delete with business rules"""
        user_ids = input_data.get('user_ids', [])
        
        if not user_ids:
            raise DomainValidationException("No user IDs provided.")
        
        if len(user_ids) > 100:
            raise DomainValidationException("Cannot delete more than 100 users at once.")
        
        # Business rule: Cannot include self in bulk delete
        if user and user.id in user_ids:
            raise DomainValidationException("Cannot delete your own account in bulk operation.")
        
        # Business rule: Cannot delete super admins unless you're super admin
        for user_id in user_ids:
            target_user = await self.user_repository.get_by_id(user_id)
            if target_user and hasattr(target_user, 'is_superuser') and target_user.is_superuser:
                if not user or not hasattr(user, 'is_superuser') or not user.is_superuser:
                    raise DomainValidationException(
                        f"Cannot delete super admin with ID: {user_id}"
                    )
        
        # Perform bulk delete
        deleted_count = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                success = await self.user_repository.delete(user_id, user, ctx)
                if success:
                    deleted_count += 1
                else:
                    failed_users.append(user_id)
            except Exception as e:
                logger.error(f"Failed to delete user {user_id}: {str(e)}")
                failed_users.append(user_id)
        
        # Return response schema
        return DeleteResponseSchema(
            id=0,  # No single ID for bulk operation
            deleted=deleted_count > 0,
            message=f"Deleted {deleted_count} users. Failed: {len(failed_users)}"
        )
