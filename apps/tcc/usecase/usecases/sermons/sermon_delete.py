from typing import Dict, Any
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.s_exceptions import (
    InvalidInputException,
    SermonNotFoundException
)

class DeleteSermonUseCase(BaseUseCase):
    """Use case for soft deleting sermons"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_sermons']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        sermon_id = input_data.get('sermon_id')
        if not sermon_id:
            raise InvalidInputException(details={
                "message": "Sermon ID is required",
                "field": "sermon_id"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        sermon_id = input_data['sermon_id']
        
        # Check if sermon exists before deletion
        existing_sermon = await self.sermon_repository.get_by_id(sermon_id, user)
        if not existing_sermon:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        # Soft delete sermon
        success = await self.sermon_repository.delete(sermon_id, user)
        
        if not success:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        return {
            "message": "Sermon deleted successfully",
            "sermon_id": sermon_id
        }