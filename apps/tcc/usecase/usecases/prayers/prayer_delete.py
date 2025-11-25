# apps/tcc/usecase/usecases/prayer/delete_prayer_uc.py
from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.p_exceptions import (
    InvalidPrayerInputException,
    PrayerRequestNotFoundException,
    PrayerResponseNotAllowedException
)
from apps.core.schemas.common.response import APIResponse


class DeletePrayerRequestUseCase(BaseUseCase):
    """Use case for soft deleting prayer requests"""
    
    def __init__(self, prayer_repository: PrayerRepository):
        super().__init__()
        self.prayer_repository = prayer_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        prayer_id = input_data.get('prayer_id')
        if not prayer_id:
            raise InvalidPrayerInputException(
                field_errors={"prayer_id": ["Prayer ID is required"]},
                user_message="Prayer request ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        prayer_id = input_data['prayer_id']
        
        # Verify prayer exists
        existing_prayer = await self.prayer_repository.get_by_id(prayer_id)
        if not existing_prayer:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        # Check if user owns the prayer or has admin permissions
        if existing_prayer.user_id != user.id and not getattr(user, 'is_staff', False):
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
        
        return APIResponse.success_response(
            message="Prayer request deleted successfully",
            data={"prayer_id": prayer_id}
        )