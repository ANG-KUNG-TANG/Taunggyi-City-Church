# from typing import Dict, Any, List
# from apps.core.schemas.builders.prayer_re_builder import PrayerResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.p_exceptions import (
#     InvalidPrayerInputException
# )
# from apps.tcc.usecase.entities.prayer import PrayerRequestEntity
# from apps.core.schemas.schemas.prayer import PrayerRequestCreate
# from apps.tcc.models.base.enums import PrayerPrivacy


# class CreatePrayerRequestUseCase(BaseUseCase):
#     """Use case for creating new prayer requests"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         # Validate using Pydantic schema
#         try:
#             # Add user_id from context to input data
#             input_data_with_user = input_data.copy()
#             input_data_with_user['user_id'] = context.user.id
            
#             validated_data = PrayerRequestCreate(**input_data_with_user)
#         except Exception as e:
#             field_errors = self._extract_pydantic_errors(e)
#             raise InvalidPrayerInputException(
#                 field_errors=field_errors,
#                 user_message="Please check your prayer request data and try again."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         # Create PrayerRequestEntity with user from context
#         prayer_data = PrayerRequestCreate(
#             **input_data,
#             user_id=user.id
#         )
        
#         prayer_entity = PrayerRequestEntity(prayer_data=prayer_data)
#         prayer_entity.prepare_for_persistence()
        
#         # Create prayer request using repository
#         created_prayer = await self.prayer_repository.create(prayer_entity)
        
#         # Build response using builder
#         prayer_response = PrayerResponseBuilder.to_response(created_prayer)
        
#         return APIResponse.success_response(
#             message="Prayer request created successfully",
#             data=prayer_response.model_dump()
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