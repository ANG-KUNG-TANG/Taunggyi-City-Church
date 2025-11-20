# sermon_update.py
from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.s_exceptions import (
    InvalidInputException,
    SermonNotFoundException
)
from entities.sermons import SermonEntity
from apps.tcc.models.base.enums import SermonStatus

class UpdateSermonUseCase(BaseUseCase):
    """Use case for updating sermon"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
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
        
        # Check if sermon exists
        existing_sermon = await self.sermon_repository.get_by_id(sermon_id)
        if not existing_sermon:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        # Create updated SermonEntity
        updated_sermon_entity = SermonEntity(
            id=sermon_id,
            title=input_data.get('title', existing_sermon.title),
            preacher=input_data.get('preacher', existing_sermon.preacher),
            bible_passage=input_data.get('bible_passage', existing_sermon.bible_passage),
            description=input_data.get('description', existing_sermon.description),
            content=input_data.get('content', existing_sermon.content),
            sermon_date=input_data.get('sermon_date', existing_sermon.sermon_date),
            duration_minutes=input_data.get('duration_minutes', existing_sermon.duration_minutes),
            audio_url=input_data.get('audio_url', existing_sermon.audio_url),
            video_url=input_data.get('video_url', existing_sermon.video_url),
            status=input_data.get('status', existing_sermon.status),
            is_active=existing_sermon.is_active,
            created_at=existing_sermon.created_at,
            updated_at=existing_sermon.updated_at
        )
        
        # Update sermon using repository
        updated_sermon = await self.sermon_repository.update(sermon_id, updated_sermon_entity)
        
        if not updated_sermon:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        return {
            "message": "Sermon updated successfully",
            "sermon": self._format_sermon_response(updated_sermon)
        }

    @staticmethod
    def _format_sermon_response(sermon_entity):
        """Format sermon entity for response"""
        return {
            'id': sermon_entity.id,
            'title': sermon_entity.title,
            'preacher': sermon_entity.preacher,
            'bible_passage': sermon_entity.bible_passage,
            'sermon_date': sermon_entity.sermon_date,
            'status': sermon_entity.status.value if hasattr(sermon_entity.status, 'value') else sermon_entity.status,
            'updated_at': sermon_entity.updated_at
        }