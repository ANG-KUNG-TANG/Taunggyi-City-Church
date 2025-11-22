from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.s_exceptions import (
    InvalidInputException,
    SermonNotFoundException
)
from entities.sermons import SermonEntity
from apps.tcc.models.base.enums import SermonStatus

class CreateSermonUseCase(BaseUseCase):
    """Use case for creating new sermons"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_sermons']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['title', 'preacher', 'sermon_date']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise InvalidInputException(details={
                "message": "Missing required fields",
                "fields": missing_fields
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Convert input to SermonEntity
        sermon_entity = SermonEntity(
            title=input_data['title'],
            preacher=input_data['preacher'],
            sermon_date=input_data['sermon_date'],
            bible_passage=input_data.get('bible_passage'),
            description=input_data.get('description'),
            content=input_data.get('content'),
            duration_minutes=input_data.get('duration_minutes'),
            audio_url=input_data.get('audio_url'),
            video_url=input_data.get('video_url'),
            status=input_data.get('status', SermonStatus.DRAFT)
        )
        
        # Create sermon using repository
        created_sermon = await self.sermon_repository.create(sermon_entity)
        
        return {
            "message": "Sermon created successfully",
            "sermon": self._format_sermon_response(created_sermon)
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
            'duration_minutes': sermon_entity.duration_minutes,
            'audio_url': sermon_entity.audio_url,
            'video_url': sermon_entity.video_url,
            'status': sermon_entity.status.value if hasattr(sermon_entity.status, 'value') else sermon_entity.status,
            'created_at': sermon_entity.created_at,
            'updated_at': sermon_entity.updated_at
        }