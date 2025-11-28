# from typing import Dict, Any, List, Optional
# from apps.tcc.usecase.repo.domain_repo.donations import DonationRepository, FundRepository
# from usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
# from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
# from apps.tcc.usecase.domain_exception.d_exceptions import (
#     DonationException,
#     DonationNotFoundException
# )
# # Import Response Builder
# from apps.core.schemas.builders.donation_rp_builder import DonationResponseBuilder, FundTypeResponseBuilder


# class GetDonationByIdUseCase(BaseUseCase):
#     """Use case for getting donation by ID"""
    
        
#     def __init__(self, donation_repository: DonationRepository):
#         super().__init__()
#         self.donation_repository = donation_repository
    
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         donation_id = input_data.get('donation_id')
#         if not donation_id:
#             raise DonationException(
#                 message="Donation ID is required",
#                 error_code="MISSING_DONATION_ID",
#                 user_message="Donation ID is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         donation_id = input_data['donation_id']
#         donation_entity = await self.donation_repository.get_by_id(donation_id)
        
#         if not donation_entity:
#             raise DonationNotFoundException(
#                 donation_id=str(donation_id),
#                 user_message="Donation not found."
#             )
        
#         return {
#             "donation": DonationResponseBuilder.to_response(donation_entity).model_dump()
#         }


# class GetAllDonationsUseCase(BaseUseCase):
#     """Use case for getting all donations with optional filtering"""
    
#     def __init__(self):
#         super().__init__()
#         self.donation_repository = DonationRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         filters = input_data.get('filters', {})
#         donations = await self.donation_repository.get_all(filters)
        
#         list_response = DonationResponseBuilder.to_list_response(
#             donations,
#             total=len(donations), # Placeholder, actual total should come from repo if paginated
#             page=input_data.get('page', 1),
#             per_page=input_data.get('per_page', 20)
#         )
        
#         return list_response.model_dump()


# class GetUserDonationsUseCase(BaseUseCase):
#     """Use case for getting all donations by a user"""
    
#     def __init__(self):
#         super().__init__()
#         self.donation_repository = DonationRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         donations = await self.donation_repository.get_user_donations(user.id)
        
#         list_response = DonationResponseBuilder.to_list_response(
#             donations,
#             total=len(donations)
#         )
        
#         return list_response.model_dump()


# class GetDonationsByStatusUseCase(BaseUseCase):
#     """Use case for getting donations by status"""
    
#     def __init__(self):
#         super().__init__()
#         self.donation_repository = DonationRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         status = input_data.get('status')
#         if not status:
#             raise DonationException(
#                 message="Status is required",
#                 error_code="MISSING_STATUS",
#                 user_message="Donation status is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         status = input_data['status']
#         donations = await self.donation_repository.get_donations_by_status(status)
        
#         list_response = DonationResponseBuilder.to_list_response(
#             donations,
#             total=len(donations)
#         )
        
#         return list_response.model_dump()


# class GetFundTypeByIdUseCase(BaseUseCase):
#     """Use case for getting fund type by ID"""
    
#     def __init__(self):
#         super().__init__()
#         self.fund_repository = FundRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         fund_id = input_data.get('fund_id')
#         if not fund_id:
#             raise DonationException(
#                 message="Fund ID is required",
#                 error_code="MISSING_FUND_ID",
#                 user_message="Fund ID is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         fund_id = input_data['fund_id']
#         fund_entity = await self.fund_repository.get_by_id(fund_id)
        
#         if not fund_entity:
#             raise DonationException(
#                 message=f"Fund {fund_id} not found",
#                 error_code="FUND_NOT_FOUND",
#                 user_message="Fund not found."
#             )
        
#         return {
#             "fund": FundTypeResponseBuilder.to_response(fund_entity).model_dump()
#         }


# class GetAllFundTypesUseCase(BaseUseCase):
#     """Use case for getting all fund types"""
    
#     def __init__(self):
#         super().__init__()
#         self.fund_repository = FundRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         filters = input_data.get('filters', {})
#         funds = await self.fund_repository.get_all(filters)
        
#         list_response = FundTypeResponseBuilder.to_list_response(
#             funds,
#             total=len(funds), # Placeholder
#             page=input_data.get('page', 1),
#             per_page=input_data.get('per_page', 20)
#         )
        
#         return list_response.model_dump()


# class GetActiveFundTypesUseCase(BaseUseCase):
#     """Use case for getting active fund types"""
    
#     def __init__(self):
#         super().__init__()
#         self.fund_repository = FundRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         funds = await self.fund_repository.get_active_funds()
        
#         list_response = FundTypeResponseBuilder.to_list_response(
#             funds,
#             total=len(funds)
#         )
        
#         return list_response.model_dump()


# class GetDonationsByFundUseCase(BaseUseCase):
#     """Use case for getting donations by fund"""
    
#     def __init__(self):
#         super().__init__()
#         self.donation_repository = DonationRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         fund_id = input_data.get('fund_id')
#         if not fund_id:
#             raise DonationException(
#                 message="Fund ID is required",
#                 error_code="MISSING_FUND_ID",
#                 user_message="Fund ID is required."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         fund_id = input_data['fund_id']
#         donations = await self.donation_repository.get_donations_by_fund(fund_id)
        
#         list_response = DonationResponseBuilder.to_list_response(
#             donations,
#             total=len(donations)
#         )
        
#         response_data = list_response.model_dump()
#         response_data["fund_id"] = fund_id
#         return response_data


# class GetDonationStatsUseCase(BaseUseCase):
#     """Use case for getting donation statistics"""
    
#     def __init__(self):
#         super().__init__()
#         self.donation_repository = DonationRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         stats = await self.donation_repository.get_donation_stats()
        
#         return {
#             "statistics": stats
#         }