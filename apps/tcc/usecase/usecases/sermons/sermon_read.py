# sermon_read.py
from typing import Dict, Any, List
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from usecases.base.base_uc import BaseUseCase
from usecase.domain_exception.s_exceptions import (
    InvalidInputException,
    SermonNotFoundException
)
from apps.tcc.models.base.enums import SermonStatus

class GetSermonByIdUseCase(BaseUseCase):
    """Use case for getting sermon by ID"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        sermon_id = input_data.get('sermon_id')
        if not sermon_id:
            raise InvalidInputException(details={
                "message": "Sermon ID is required",
                "field": "sermon_id"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        sermon_id = input_data['sermon_id']
        sermon_entity = await self.sermon_repository.get_by_id(sermon_id)
        
        if not sermon_entity:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        return self._format_sermon_response(sermon_entity)

class GetRecentSermonsUseCase(BaseUseCase):
    """Use case for getting recent sermons"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        limit = input_data.get('limit', 10)
        sermons = await self.sermon_repository.get_recent_sermons(limit)
        
        return {
            "sermons": [self._format_sermon_response(sermon) for sermon in sermons],
            "total_count": len(sermons)
        }

class GetSermonsByPreacherUseCase(BaseUseCase):
    """Use case for getting sermons by preacher"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        preacher = input_data.get('preacher')
        if not preacher:
            raise InvalidInputException(details={
                "message": "Preacher name is required",
                "field": "preacher"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        preacher = input_data['preacher']
        sermons = await self.sermon_repository.get_sermons_by_preacher(preacher)
        
        return {
            "sermons": [self._format_sermon_response(sermon) for sermon in sermons],
            "preacher": preacher,
            "total_count": len(sermons)
        }

class GetSermonsByDateRangeUseCase(BaseUseCase):
    """Use case for getting sermons by date range"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        start_date = input_data.get('start_date')
        end_date = input_data.get('end_date')
        
        if not start_date or not end_date:
            raise InvalidInputException(details={
                "message": "Both start_date and end_date are required",
                "fields": ["start_date", "end_date"]
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        start_date = input_data['start_date']
        end_date = input_data['end_date']
        sermons = await self.sermon_repository.get_sermons_by_date_range(start_date, end_date)
        
        return {
            "sermons": [self._format_sermon_response(sermon) for sermon in sermons],
            "start_date": start_date,
            "end_date": end_date,
            "total_count": len(sermons)
        }

class SearchSermonsUseCase(BaseUseCase):
    """Use case for searching sermons"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term:
            raise InvalidInputException(details={
                "message": "Search term is required",
                "field": "search_term"
            })

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        search_term = input_data['search_term']
        sermons = await self.sermon_repository.search_sermons(search_term)
        
        return {
            "sermons": [self._format_sermon_response(sermon) for sermon in sermons],
            "search_term": search_term,
            "total_count": len(sermons)
        }

class GetAllSermonsUseCase(BaseUseCase):
    """Use case for getting all sermons with optional filtering"""
    
    def __init__(self):
        super().__init__()
        self.sermon_repository = SermonRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        sermons = await self.sermon_repository.get_all(filters)
        
        return {
            "sermons": [self._format_sermon_response(sermon) for sermon in sermons],
            "total_count": len(sermons)
        }

class PublishSermonUseCase(BaseUseCase):
    """Use case for publishing a sermon"""
    
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
        
        # Publish sermon using repository
        published_sermon = await self.sermon_repository.publish_sermon(sermon_id)
        
        if not published_sermon:
            raise SermonNotFoundException(sermon_id=sermon_id)
        
        return {
            "message": "Sermon published successfully",
            "sermon": self._format_sermon_response(published_sermon)
        }

# Common response formatting method
def _format_sermon_response(sermon_entity):
    """Format sermon entity for response"""
    return {
        'id': sermon_entity.id,
        'title': sermon_entity.title,
        'preacher': sermon_entity.preacher,
        'bible_passage': sermon_entity.bible_passage,
        'description': sermon_entity.description,
        'sermon_date': sermon_entity.sermon_date,
        'duration_minutes': sermon_entity.duration_minutes,
        'audio_url': sermon_entity.audio_url,
        'video_url': sermon_entity.video_url,
        'status': sermon_entity.status.value if hasattr(sermon_entity.status, 'value') else sermon_entity.status,
        'is_active': sermon_entity.is_active,
        'created_at': sermon_entity.created_at,
        'updated_at': sermon_entity.updated_at
    }

# Attach the formatting method to all read use cases
for cls in [GetSermonByIdUseCase, GetRecentSermonsUseCase, GetSermonsByPreacherUseCase,
           GetSermonsByDateRangeUseCase, SearchSermonsUseCase, GetAllSermonsUseCase, PublishSermonUseCase]:
    cls._format_sermon_response = staticmethod(_format_sermon_response)