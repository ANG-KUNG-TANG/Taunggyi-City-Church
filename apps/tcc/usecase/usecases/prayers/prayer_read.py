# from typing import Dict, Any, List
# from apps.core.schemas.builders.prayer_re_builder import PrayerResponseBuilder
# from apps.core.schemas.common.response import APIResponse
# from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.domain_exception.p_exceptions import (
#     InvalidPrayerInputException,
#     PrayerRequestNotFoundException
# )


# class GetPrayerRequestByIdUseCase(BaseUseCase):
#     """Use case for getting prayer request by ID"""
    
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
#                 user_message="Please provide a valid prayer ID."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         prayer_id = input_data['prayer_id']
#         prayer_entity = await self.prayer_repository.get_by_id(prayer_id)
        
#         if not prayer_entity:
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found."
#             )
        
#         # Check if user can view this prayer
#         if not prayer_entity.can_view(user):
#             raise PrayerRequestNotFoundException(
#                 prayer_id=str(prayer_id),
#                 user_message="Prayer request not found or access denied."
#             )
        
#         # Use builder for response
#         prayer_response = PrayerResponseBuilder.to_response(prayer_entity)
        
#         return APIResponse.success_response(
#             message="Prayer request retrieved successfully",
#             data=prayer_response.model_dump()
#         )


# class GetAllPrayerRequestsUseCase(BaseUseCase):
#     """Use case for getting all prayer requests with pagination"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         # Get prayers with pagination
#         prayers, total_count = await self.prayer_repository.get_all_paginated(
#             page=page,
#             per_page=per_page,
#             user_id=user.id  # Only get prayers user can view
#         )
        
#         # Use builder for list response
#         list_response = PrayerResponseBuilder.to_list_response(
#             entities=prayers,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message="Prayer requests retrieved successfully",
#             data=list_response.model_dump()
#         )


# class GetPublicPrayerRequestsUseCase(BaseUseCase):
#     """Use case for getting public prayer requests"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = False

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         prayers, total_count = await self.prayer_repository.get_public_prayers_paginated(
#             page=page,
#             per_page=per_page
#         )
        
#         # Convert to public responses
#         public_responses = [PrayerResponseBuilder.to_public_response(prayer) for prayer in prayers]
        
#         return APIResponse.success_response(
#             message="Public prayer requests retrieved successfully",
#             data={
#                 "prayer_requests": public_responses,
#                 "total": total_count,
#                 "page": page,
#                 "per_page": per_page,
#                 "total_pages": (total_count + per_page - 1) // per_page if per_page > 0 else 1
#             }
#         )


# class GetUserPrayerRequestsUseCase(BaseUseCase):
#     """Use case for getting prayer requests by current user"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         prayers, total_count = await self.prayer_repository.get_user_prayers_paginated(
#             user_id=user.id,
#             page=page,
#             per_page=per_page
#         )
        
#         list_response = PrayerResponseBuilder.to_list_response(
#             entities=prayers,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message="Your prayer requests retrieved successfully",
#             data=list_response.model_dump()
#         )


# class GetPrayerRequestsByPrivacyUseCase(BaseUseCase):
#     """Use case for getting prayers by privacy level"""
    
#     def __init__(self, prayer_repository: PrayerRepository):
#         super().__init__()
#         self.prayer_repository = prayer_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         privacy = input_data.get('privacy')
#         if not privacy:
#             raise InvalidPrayerInputException(
#                 field_errors={"privacy": ["Privacy level is required"]},
#                 user_message="Prayer privacy level is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> APIResponse:
#         privacy = input_data['privacy']
#         page = input_data.get('page', 1)
#         per_page = input_data.get('per_page', 20)
        
#         prayers, total_count = await self.prayer_repository.get_prayers_by_privacy_paginated(
#             privacy=privacy,
#             user_id=user.id,
#             page=page,
#             per_page=per_page
#         )
        
#         list_response = PrayerResponseBuilder.to_list_response(
#             entities=prayers,
#             total=total_count,
#             page=page,
#             per_page=per_page
#         )
        
#         return APIResponse.success_response(
#             message=f"Prayer requests with privacy '{privacy}' retrieved successfully",
#             data=list_response.model_dump()
#         )