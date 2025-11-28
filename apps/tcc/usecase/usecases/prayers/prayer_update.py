# from typing import Dict, Any, List
# from apps.core.schemas.builders.prayer_re_builder import PrayerResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.p_exceptions import (
#     InvalidPrayerInputException,
#     PrayerRequestNotFoundException,
#     PrayerRequestAlreadyAnsweredException,
#     PrayerResponseNotAllowedException
# )
# from apps.tcc.usecase.entities.prayer import PrayerRequestEntity
# from apps.core.schemas.schemas.prayer import PrayerRequestUpdate


# class UpdatePrayerRequestUseCase(BaseUseCase):
#     """Use case for updating prayer requests"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         prayer_id = input_data.get('prayer_id')
#         if not prayer_id:
#             raise InvalidPrayerInputException(
#                 field_errors={"prayer_id": ["Prayer ID is required"]},
#                 user_message="Prayer request ID is required."
#             )
        
#         # Validate update data using schema
#         update_data = input_data.get('update_data', {})
#         try:
#             validated_data = PrayerRequestUpdate(**update_data)
#         except Exception as e:
#             field_errors = self._extract_pydantic_errors(e)
#             raise InvalidPrayerInputException(
#                 field_errors=field_errors,
#                 user_message="Please check your update data and try again."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         prayer_id = input_data['prayer_id']
#         update_data = input_data.get('update_data', {})
        
#         # Check if prayer exists
#         existing_prayer = await self.prayer_repository.get_by_id(prayer_id)
#         if not existing_prayer:
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found."
#             )
        
#         # Check if user owns the prayer
#         if existing_prayer.user_id != user.id:
#             raise PrayerResponseNotAllowedException(
#                 prayer_id=str(prayer_id),
#                 user_id=str(user.id),
#                 reason="User is not the owner of this prayer request",
#                 user_message="You can only update your own prayer requests."
#             )
        
#         # Check if prayer is already answered
#         if existing_prayer.is_answered:
#             raise PrayerRequestAlreadyAnsweredException(
#                 prayer_id=str(prayer_id),
#                 answered_at=str(existing_prayer.updated_at),
#                 user_message="Cannot update an answered prayer request."
#             )
        
#         # Create updated PrayerRequestEntity
#         updated_prayer_entity = self._create_updated_entity(existing_prayer, update_data)
        
#         # Update prayer request using repository
#         updated_prayer = await self.prayer_repository.update(prayer_id, updated_prayer_entity)
        
#         if not updated_prayer:
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found for update."
#             )
        
#         # Use builder for response
#         prayer_response = PrayerResponseBuilder.to_response(updated_prayer)
        
#         return APIResponse.success_response(
#             message="Prayer request updated successfully",
#             data=prayer_response.model_dump()
#         )

#     def _create_updated_entity(self, existing_prayer: PrayerRequestEntity, update_data: Dict[str, Any]) -> PrayerRequestEntity:
#         """Create updated PrayerRequestEntity from existing prayer and update data"""
#         # Build kwargs for PrayerRequestEntity constructor
#         entity_kwargs = {
#             "id": existing_prayer.id,
#             "user_id": existing_prayer.user_id,
#             "title": update_data.get('title', existing_prayer.title),
#             "content": update_data.get('content', existing_prayer.content),
#             "privacy": update_data.get('privacy', existing_prayer.privacy),
#             "expires_at": update_data.get('expires_at', existing_prayer.expires_at),
#             "answer_notes": update_data.get('answer_notes', existing_prayer.answer_notes),
#             "is_answered": update_data.get('is_answered', existing_prayer.is_answered),
#             "prayer_count": existing_prayer.prayer_count,
#             "created_at": existing_prayer.created_at,
#             "updated_at": existing_prayer.updated_at
#         }
        
#         return PrayerRequestEntity(**entity_kwargs)

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


# class MarkPrayerRequestAnsweredUseCase(BaseUseCase):
#     """Use case for marking prayer requests as answered"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         prayer_id = input_data.get('prayer_id')
#         if not prayer_id:
#             raise InvalidPrayerInputException(
#                 field_errors={"prayer_id": ["Prayer ID is required"]},
#                 user_message="Prayer request ID is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         prayer_id = input_data['prayer_id']
#         answer_notes = input_data.get('answer_notes', '')
        
#         # Check if prayer exists and user has permission
#         existing_prayer = await self.prayer_repository.get_by_id(prayer_id)
#         if not existing_prayer:
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found."
#             )
        
#         # Only prayer owner or admin can mark as answered
#         if existing_prayer.user_id != user.id and not getattr(user, 'is_staff', False):
#             raise PrayerResponseNotAllowedException(
#                 prayer_id=str(prayer_id),
#                 user_id=str(user.id),
#                 reason="User is not the owner of this prayer request",
#                 user_message="You can only mark your own prayer requests as answered."
#             )
        
#         # Mark prayer as answered using repository
#         prayer_entity = await self.prayer_repository.mark_as_answered(prayer_id, answer_notes)
        
#         if not prayer_entity:
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found."
#             )
        
#         prayer_response = PrayerResponseBuilder.to_response(prayer_entity)
        
#         return APIResponse.success_response(
#             message="Prayer request marked as answered successfully",
#             data=prayer_response.model_dump()
#         )