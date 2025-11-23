from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.s_exceptions import (
    InvalidSermonInputException,
    SermonNotFoundException
)
from apps.core.schemas.common.response import APIResponse


class DeleteSermonUseCase(BaseUseCase):
    """Use case for soft deleting sermons"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_sermons']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        sermon_id = input_data.get('sermon_id')
        if not sermon_id:
            raise InvalidSermonInputException(
                field_errors={"sermon_id": ["Sermon ID is required"]},
                user_message="Please provide a valid sermon ID."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        sermon_id = input_data['sermon_id']
        
        # Check if sermon exists before deletion
        existing_sermon = await self.sermon_repository.get_by_id(sermon_id)
        if not existing_sermon:
            raise SermonNotFoundException(
                sermon_id=sermon_id,
                user_message="Sermon not found."
            )
        
        # Soft delete sermon
        success = await self.sermon_repository.delete(sermon_id)
        
        if not success:
            raise SermonNotFoundException(
                sermon_id=sermon_id,
                user_message="Failed to delete sermon."
            )
        
        return APIResponse.success_response(
            message="Sermon deleted successfully",
            data={"sermon_id": sermon_id}
        )