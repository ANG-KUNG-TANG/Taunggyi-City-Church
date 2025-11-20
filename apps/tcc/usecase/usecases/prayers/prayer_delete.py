# prayer_delete.py
from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository, PrayerResponseRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.p_exceptions import (
    PrayerException,
    PrayerRequestNotFoundException,
    PrayerResponseNotAllowedException
)


class DeletePrayerRequestUseCase(BaseUseCase):
    """Use case for soft deleting prayer requests"""
    
    def __init__(self):
        super().__init__()
        self.prayer_repository = PrayerRepository()  
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        prayer_id = input_data.get('prayer_id')
        if not prayer_id:
            raise PrayerException(
                message="Prayer ID is required",
                error_code="MISSING_PRAYER_ID",
                user_message="Prayer request ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        prayer_id = input_data['prayer_id']
        
        # Verify prayer exists and user has permission
        existing_prayer = await self.prayer_repository.get_by_id(prayer_id)
        if not existing_prayer:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        # Check if user owns the prayer or has admin permissions
        if existing_prayer.user_id != user.id and not getattr(user, 'can_manage_prayers', False):
            raise PrayerResponseNotAllowedException(
                prayer_id=str(prayer_id),
                user_id=str(user.id),
                reason="User is not the owner of this prayer request",
                user_message="You can only delete your own prayer requests."
            )
        
        # Soft delete prayer request
        result = await self.prayer_repository.delete(prayer_id)
        
        if not result:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found for deletion."
            )
        
        return {
            "message": "Prayer request deleted successfully",
            "prayer_id": prayer_id
        }


class DeletePrayerResponseUseCase(BaseUseCase):
    """Use case for deleting prayer responses"""
    
    def __init__(self):
        super().__init__()
        self.prayer_response_repository = PrayerResponseRepository() 
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        response_id = input_data.get('response_id')
        if not response_id:
            raise PrayerException(
                message="Response ID is required",
                error_code="MISSING_RESPONSE_ID",
                user_message="Prayer response ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        response_id = input_data['response_id']
        
        # Get existing response to verify ownership
        existing_response = await self.prayer_response_repository.get_by_id(response_id)
        if not existing_response:
            raise PrayerException(
                message=f"Prayer response {response_id} not found",
                error_code="PRAYER_RESPONSE_NOT_FOUND",
                user_message="Prayer response not found."
            )
        
        # Only allow the response owner to delete
        if existing_response.user_id != user.id and not getattr(user, 'can_manage_prayers', False):
            raise PrayerResponseNotAllowedException(
                prayer_id=str(existing_response.prayer_request_id),
                user_id=str(user.id),
                reason="User is not the owner of this response",
                user_message="You can only delete your own prayer responses."
            )
        
        result = await self.prayer_response_repository.delete(response_id)
        
        if not result:
            raise PrayerException(
                message=f"Prayer response {response_id} not found for deletion",
                error_code="PRAYER_RESPONSE_DELETION_FAILED",
                user_message="Prayer response not found for deletion."
            )
        
        return {
            "message": "Prayer response deleted successfully",
            "response_id": response_id
        }