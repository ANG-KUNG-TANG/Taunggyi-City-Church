# from typing import Dict, Any, List
# from apps.core.schemas.builders.sermon_rp_builder import SermonResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.s_exceptions import (
#     InvalidSermonInputException, 
#     SermonAlreadyExistsException
# )
# from apps.tcc.usecase.entities.sermons import SermonEntity
# from apps.core.schemas.schemas.sermons import SermonCreateSchema


# class CreateSermonUseCase(BaseUseCase):
#     """Sermon creation use case following user use case pattern"""
    
#     def __init__(self, sermon_repository: SermonRepository):
#         super().__init__()
#         self.sermon_repository = sermon_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_sermons']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         # Validate using Pydantic schema
#         try:
#             validated_data = SermonCreateSchema(**input_data)
#         except Exception as e:
#             field_errors = self._extract_pydantic_errors(e)
#             raise InvalidSermonInputException(
#                 field_errors=field_errors,
#                 user_message="Please check your sermon data and try again."
#             )

#         # Check if sermon with same title and date already exists
#         if await self.sermon_repository.exists_by_title_and_date(
#             validated_data.title, validated_data.sermon_date
#         ):
#             raise SermonAlreadyExistsException(
#                 title=validated_data.title,
#                 sermon_date=validated_data.sermon_date,
#                 user_message="A sermon with this title and date already exists."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         # Create and persist sermon
#         sermon_entity = SermonEntity(sermon_data=SermonCreateSchema(**input_data))
#         sermon_entity.prepare_for_persistence()
#         created_sermon = await self.sermon_repository.create(sermon_entity)

#         # Build response using builder
#         sermon_response = SermonResponseBuilder.to_response(created_sermon)
        
#         return APIResponse.success_response(
#             message="Sermon created successfully",
#             data=sermon_response.model_dump()
#         )

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