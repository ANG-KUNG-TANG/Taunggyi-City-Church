# from typing import Dict, Any, List
# from apps.core.schemas.builders.sermon_rp_builder import SermonResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.s_exceptions import (
#     InvalidSermonInputException,
#     SermonNotFoundException
# )
# from apps.tcc.usecase.entities.sermons import SermonEntity
# from apps.core.schemas.schemas.sermons import SermonUpdateSchema


# class UpdateSermonUseCase(BaseUseCase):
#     """Use case for updating sermon with JWT context"""
    
#     def __init__(self, sermon_repository: SermonRepository):
#         super().__init__()
#         self.sermon_repository = sermon_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_sermons']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         sermon_id = input_data.get('sermon_id')
#         if not sermon_id:
#             raise InvalidSermonInputException(
#                 field_errors={"sermon_id": ["Sermon ID is required"]},
#                 user_message="Please provide a valid sermon ID."
#             )
        
#         # Validate update data using schema
#         update_data = input_data.get('update_data', {})
#         try:
#             validated_data = SermonUpdateSchema(**update_data)
#         except Exception as e:
#             field_errors = self._extract_pydantic_errors(e)
#             raise InvalidSermonInputException(
#                 field_errors=field_errors,
#                 user_message="Please check your update data and try again."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         sermon_id = input_data['sermon_id']
#         update_data = input_data.get('update_data', {})
        
#         # Check if sermon exists
#         existing_sermon = await self.sermon_repository.get_by_id(sermon_id)
#         if not existing_sermon:
#             raise SermonNotFoundException(
#                 sermon_id=sermon_id,
#                 user_message="Sermon not found."
#             )
        
#         # Create updated SermonEntity from validated data
#         validated_update = SermonUpdateSchema(**update_data)
#         updated_sermon_entity = self._create_updated_entity(existing_sermon, validated_update)
        
#         # Update sermon using repository
#         updated_sermon = await self.sermon_repository.update(sermon_id, updated_sermon_entity)
        
#         if not updated_sermon:
#             raise SermonNotFoundException(
#                 sermon_id=sermon_id,
#                 user_message="Failed to update sermon."
#             )
        
#         # Use builder for response
#         sermon_response = SermonResponseBuilder.to_response(updated_sermon)
        
#         return APIResponse.success_response(
#             message="Sermon updated successfully",
#             data=sermon_response.model_dump()
#         )

#     def _create_updated_entity(self, existing_sermon: SermonEntity, update_data: SermonUpdateSchema) -> SermonEntity:
#         """Create updated SermonEntity from existing sermon and update data"""
#         update_dict = update_data.model_dump(exclude_unset=True)
        
#         # Build kwargs for SermonEntity constructor
#         entity_kwargs = {"id": existing_sermon.id}
        
#         # Add all existing attributes
#         for attr in ['title', 'preacher', 'bible_passage', 'sermon_date', 'duration', 
#                     'audio_url', 'video_url', 'thumbnail_url', 'description', 
#                     'series', 'tags', 'is_published', 'views_count', 'downloads_count',
#                     'created_at', 'updated_at']:
#             if hasattr(existing_sermon, attr):
#                 entity_kwargs[attr] = getattr(existing_sermon, attr)
        
#         # Override with updated values
#         entity_kwargs.update(update_dict)
        
#         return SermonEntity(**entity_kwargs)

#     def _extract_pydantic_errors(self, validation_error: Exception) -> Dict[str, List[str]]:
#         """Extract field errors from Pydantic validation"""
#         field_errors = {}
#         if hasattr(validation_error, 'errors'):
#             for error in validation_error.errors():
#                 field = ".".join(str(loc) for loc in error['loc'])
#                 field_errors.setdefault(field, []).append(error['msg'])
#         else:
#             field_errors['_form'] = [str(validation_error)]
#         return field_errors


# class PublishSermonUseCase(BaseUseCase):
#     """Use case for publishing/unpublishing sermons"""
    
#     def __init__(self, sermon_repository: SermonRepository):
#         super().__init__()
#         self.sermon_repository = sermon_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_sermons']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         sermon_id = input_data.get('sermon_id')
#         publish = input_data.get('publish')
        
#         if not sermon_id:
#             raise InvalidSermonInputException(
#                 field_errors={"sermon_id": ["Sermon ID is required"]},
#                 user_message="Please provide a valid sermon ID."
#             )
        
#         if publish is None:
#             raise InvalidSermonInputException(
#                 field_errors={"publish": ["Publish flag is required"]},
#                 user_message="Please specify whether to publish or unpublish."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         sermon_id = input_data['sermon_id']
#         publish = input_data['publish']
        
#         # Get existing sermon
#         existing_sermon = await self.sermon_repository.get_by_id(sermon_id)
#         if not existing_sermon:
#             raise SermonNotFoundException(
#                 sermon_id=sermon_id,
#                 user_message="Sermon not found."
#             )
        
#         # Update only the is_published field
#         updated_sermon_entity = SermonEntity(
#             id=sermon_id,
#             title=existing_sermon.title,
#             preacher=existing_sermon.preacher,
#             bible_passage=existing_sermon.bible_passage,
#             sermon_date=existing_sermon.sermon_date,
#             duration=existing_sermon.duration,
#             audio_url=existing_sermon.audio_url,
#             video_url=existing_sermon.video_url,
#             thumbnail_url=existing_sermon.thumbnail_url,
#             description=existing_sermon.description,
#             series=existing_sermon.series,
#             tags=existing_sermon.tags,
#             is_published=publish,
#             views_count=existing_sermon.views_count,
#             downloads_count=existing_sermon.downloads_count,
#             created_at=existing_sermon.created_at,
#             updated_at=existing_sermon.updated_at
#         )
        
#         # Update sermon using repository
#         updated_sermon = await self.sermon_repository.update(sermon_id, updated_sermon_entity)
        
#         if not updated_sermon:
#             raise SermonNotFoundException(
#                 sermon_id=sermon_id,
#                 user_message="Failed to update sermon publish status."
#             )
        
#         sermon_response = SermonResponseBuilder.to_response(updated_sermon)
        
#         action = "published" if publish else "unpublished"
#         return APIResponse.success_response(
#             message=f"Sermon {action} successfully",
#             data=sermon_response.model_dump()
#         )