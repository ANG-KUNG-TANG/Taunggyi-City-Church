from typing import Dict, Any, List
from apps.core.schemas.builders.sermon_rp_builder import SermonResponseBuilder
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.s_exceptions import (
    InvalidSermonInputException,
    SermonNotFoundException
)


class GetSermonByIdUseCase(BaseUseCase):
    """Use case for getting sermon by ID"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public access

    async def _validate_input(self, input_data: Dict[str, Any], context):
        sermon_id = input_data.get('sermon_id')
        if not sermon_id:
            raise InvalidSermonInputException(
                field_errors={"sermon_id": ["Sermon ID is required"]},
                user_message="Please provide a valid sermon ID."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        sermon_id = input_data['sermon_id']
        sermon_entity = await self.sermon_repository.get_by_id(sermon_id)
        
        if not sermon_entity:
            raise SermonNotFoundException(
                sermon_id=sermon_id,
                user_message="Sermon not found."
            )
        
        # Use builder to create consistent response
        sermon_response = SermonResponseBuilder.to_response(sermon_entity)
        
        return APIResponse.success_response(
            message="Sermon retrieved successfully",
            data=sermon_response.model_dump()
        )


class GetAllSermonsUseCase(BaseUseCase):
    """Use case for getting all sermons with pagination and filtering"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public access

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        preacher = input_data.get('preacher')
        year = input_data.get('year')
        series = input_data.get('series')
        
        # Get sermons with pagination
        sermons, total_count = await self.sermon_repository.get_all_paginated(
            page=page,
            per_page=per_page,
            preacher=preacher,
            year=year,
            series=series
        )
        
        # Use builder for list response
        list_response = SermonResponseBuilder.to_list_response(
            entities=sermons,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message="Sermons retrieved successfully",
            data=list_response.model_dump()
        )


class GetSermonsByPreacherUseCase(BaseUseCase):
    """Use case for getting sermons by preacher"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, input_data: Dict[str, Any], context):
        preacher = input_data.get('preacher')
        if not preacher:
            raise InvalidSermonInputException(
                field_errors={"preacher": ["Preacher name is required"]},
                user_message="Please specify a preacher."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        preacher = input_data['preacher']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        sermons, total_count = await self.sermon_repository.get_by_preacher_paginated(
            preacher=preacher,
            page=page,
            per_page=per_page
        )
        
        list_response = SermonResponseBuilder.to_list_response(
            entities=sermons,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message=f"Sermons by {preacher} retrieved successfully",
            data=list_response.model_dump()
        )


class GetRecentSermonsUseCase(BaseUseCase):
    """Use case for getting recent sermons"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        limit = input_data.get('limit', 10)
        
        sermons = await self.sermon_repository.get_recent(limit=limit)
        
        sermon_responses = [SermonResponseBuilder.to_response(sermon) for sermon in sermons]
        
        return APIResponse.success_response(
            message="Recent sermons retrieved successfully",
            data=sermon_responses
        )


class SearchSermonsUseCase(BaseUseCase):
    """Use case for searching sermons"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, input_data: Dict[str, Any], context):
        search_term = input_data.get('search_term')
        if not search_term or len(search_term.strip()) < 2:
            raise InvalidSermonInputException(
                field_errors={"search_term": ["Search term must be at least 2 characters long"]},
                user_message="Please provide a search term with at least 2 characters."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        search_term = input_data['search_term']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        sermons, total_count = await self.sermon_repository.search_sermons_paginated(
            search_term=search_term,
            page=page,
            per_page=per_page
        )
        
        list_response = SermonResponseBuilder.to_list_response(
            entities=sermons,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message=f"Search results for '{search_term}'",
            data=list_response.model_dump()
        )


class GetSermonsByYearUseCase(BaseUseCase):
    """Use case for getting sermons by year"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, input_data: Dict[str, Any], context):
        year = input_data.get('year')
        if not year:
            raise InvalidSermonInputException(
                field_errors={"year": ["Year is required"]},
                user_message="Please specify a year."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        year = input_data['year']
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        sermons, total_count = await self.sermon_repository.get_by_year_paginated(
            year=year,
            page=page,
            per_page=per_page
        )
        
        list_response = SermonResponseBuilder.to_list_response(
            entities=sermons,
            total=total_count,
            page=page,
            per_page=per_page
        )
        
        return APIResponse.success_response(
            message=f"Sermons from {year} retrieved successfully",
            data=list_response.model_dump()
        )


class GetPublicSermonUseCase(BaseUseCase):
    """Use case for getting public sermon (without sensitive data)"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _validate_input(self, input_data: Dict[str, Any], context):
        sermon_id = input_data.get('sermon_id')
        if not sermon_id:
            raise InvalidSermonInputException(
                field_errors={"sermon_id": ["Sermon ID is required"]},
                user_message="Please provide a valid sermon ID."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        sermon_id = input_data['sermon_id']
        sermon_entity = await self.sermon_repository.get_by_id(sermon_id)
        
        if not sermon_entity:
            raise SermonNotFoundException(
                sermon_id=sermon_id,
                user_message="Sermon not found."
            )
        
        public_data = SermonResponseBuilder.to_public_response(sermon_entity)
        
        return APIResponse.success_response(
            message="Public sermon data retrieved successfully",
            data=public_data
        )


class GetSermonPreviewsUseCase(BaseUseCase):
    """Use case for getting sermon previews (minimal data)"""
    
    def __init__(self, sermon_repository: SermonRepository):
        super().__init__()
        self.sermon_repository = sermon_repository
    
    def _setup_configuration(self):
        self.config.require_authentication = False

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
        limit = input_data.get('limit', 10)
        
        sermons = await self.sermon_repository.get_recent(limit=limit)
        
        previews = [SermonResponseBuilder.to_minimal_response(sermon) for sermon in sermons]
        
        return APIResponse.success_response(
            message="Sermon previews retrieved successfully",
            data=previews
        )