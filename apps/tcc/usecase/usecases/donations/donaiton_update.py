# from typing import Dict, Any
# from decimal import Decimal
# from apps.tcc.usecase.repo.domain_repo.donations import DonationRepository, FundRepository
# from usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
# from apps.tcc.models.base.enums import DonationStatus
# from apps.tcc.usecase.domain_exception.d_exceptions import (
#     DonationException,
#     DonationNotFoundException,
#     DonationAmountInvalidException,
#     FundInactiveException
# )
# # Import Schemas and Response Builder
# from apps.core.schemas.schemas.donations import DonationUpdateSchema, FundTypeUpdateSchema
# from apps.core.schemas.builders.donation_rp_builder import DonationResponseBuilder, FundTypeResponseBuilder


# class UpdateDonationUseCase(BaseUseCase):
#     """Use case for updating donations"""
        
#     def __init__(self, donation_repository: DonationRepository,fund_repository: FundRepository):
#         super().__init__()
#         self.donation_repository = donation_repository
#         self.fund_repository = fund_repository
    
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         donation_id = input_data.get('donation_id')
#         if not donation_id:
#             raise DonationException(
#                 message="Donation ID is required",
#                 error_code="MISSING_DONATION_ID",
#                 user_message="Donation ID is required."
#             )
        
#         # Validate input data using DonationUpdateSchema
#         update_data = {k: v for k, v in input_data.items() if k != 'donation_id'}
#         try:
#             DonationUpdateSchema(**update_data)
#         except Exception as e:
#              raise DonationException(
#                 message="Input validation failed",
#                 error_code="INVALID_INPUT",
#                 details={"schema_error": str(e)},
#                 user_message="Invalid data provided for donation update."
#             )
        
#         # Validate amount if provided
#         amount = input_data.get('amount')
#         if amount:
#             await self._validate_amount(amount)

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         donation_id = input_data['donation_id']
        
#         # Check if donation exists
#         existing_donation = await self.donation_repository.get_by_id(donation_id)
#         if not existing_donation:
#             raise DonationNotFoundException(
#                 donation_id=str(donation_id),
#                 user_message="Donation not found."
#             )
        
#         # Validate fund if being updated
#         if 'fund_id' in input_data and input_data['fund_id']:
#             await self._validate_fund(input_data['fund_id'])
        
#         # Create updated DonationEntity
#         updated_donation_entity = DonationEntity(
#             id=donation_id,
#             donor_id=existing_donation.donor_id,
#             fund_id=input_data.get('fund_id', existing_donation.fund_id),
#             amount=Decimal(str(input_data.get('amount', existing_donation.amount))),
#             payment_method=input_data.get('payment_method', existing_donation.payment_method),
#             status=input_data.get('status', existing_donation.status),
#             donation_date=input_data.get('donation_date', existing_donation.donation_date),
#             transaction_id=input_data.get('transaction_id', existing_donation.transaction_id),
#             is_recurring=input_data.get('is_recurring', existing_donation.is_recurring),
#             is_active=input_data.get('is_active', existing_donation.is_active),
#             created_at=existing_donation.created_at,
#             updated_at=existing_donation.updated_at
#         )
        
#         # Update donation
#         updated_donation = await self.donation_repository.update(donation_id, updated_donation_entity)
        
#         if not updated_donation:
#             raise DonationNotFoundException(
#                 donation_id=str(donation_id),
#                 user_message="Donation not found for update."
#             )
        
#         return {
#             "message": "Donation updated successfully",
#             "donation": DonationResponseBuilder.to_response(updated_donation).model_dump()
#         }

#     async def _validate_amount(self, amount: float) -> None:
#         """Validate donation amount"""
#         min_amount = Decimal('0.01')
#         max_amount = Decimal('100000.00')
#         amount_decimal = Decimal(str(amount))
        
#         if amount_decimal < min_amount or amount_decimal > max_amount:
#             raise DonationAmountInvalidException(
#                 amount=amount,
#                 min_amount=float(min_amount),
#                 max_amount=float(max_amount),
#                 user_message=f"Donation amount must be between ${min_amount:.2f} and ${max_amount:.2f}."
#             )

#     async def _validate_fund(self, fund_id: int) -> None:
#         """Validate fund is active"""
#         fund_entity = await self.fund_repository.get_by_id(fund_id)
#         if not fund_entity:
#             raise DonationException(
#                 message=f"Fund {fund_id} not found",
#                 error_code="FUND_NOT_FOUND",
#                 user_message="Selected fund not found."
#             )
        
#         if not fund_entity.is_active:
#             raise FundInactiveException(
#                 fund_id=str(fund_id),
#                 fund_name=fund_entity.name,
#                 user_message=f"Fund '{fund_entity.name}' is not currently accepting donations."
#             )


# class UpdateFundTypeUseCase(BaseUseCase):
#     """Use case for updating fund types"""
    
#     def __init__(self):
#         super().__init__()
#         self.fund_repository = FundRepository()
    
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
        
#         # Validate input data using FundTypeUpdateSchema
#         update_data = {k: v for k, v in input_data.items() if k != 'fund_id'}
#         try:
#             FundTypeUpdateSchema(**update_data)
#         except Exception as e:
#              raise DonationException(
#                 message="Input validation failed",
#                 error_code="INVALID_INPUT",
#                 details={"schema_error": str(e)},
#                 user_message="Invalid data provided for fund type update."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         fund_id = input_data['fund_id']
        
#         # Check if fund exists
#         existing_fund = await self.fund_repository.get_by_id(fund_id)
#         if not existing_fund:
#             raise DonationException(
#                 message=f"Fund {fund_id} not found",
#                 error_code="FUND_NOT_FOUND",
#                 user_message="Fund not found."
#             )
        
#         # Create updated FundTypeEntity
#         updated_fund_entity = FundTypeEntity(
#             id=fund_id,
#             name=input_data.get('name', existing_fund.name),
#             description=input_data.get('description', existing_fund.description),
#             target_amount=Decimal(str(input_data['target_amount'])) if input_data.get('target_amount') is not None else existing_fund.target_amount,
#             current_amount=Decimal(str(input_data.get('current_balance', existing_fund.current_amount))),
#             is_active=input_data.get('is_active', existing_fund.is_active),
#             created_at=existing_fund.created_at,
#             updated_at=existing_fund.updated_at
#         )
        
#         # Update fund type
#         updated_fund = await self.fund_repository.update(fund_id, updated_fund_entity)
        
#         if not updated_fund:
#             raise DonationException(
#                 message=f"Fund {fund_id} not found for update",
#                 error_code="FUND_UPDATE_FAILED",
#                 user_message="Fund not found for update."
#             )
        
#         return {
#             "message": "Fund type updated successfully",
#             "fund": FundTypeResponseBuilder.to_response(updated_fund).model_dump()
#         }