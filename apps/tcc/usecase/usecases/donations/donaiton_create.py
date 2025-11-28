# from typing import Dict, Any
# from decimal import Decimal
# from apps.core.schemas.builders.donation_rp_builder import DonationResponseBuilder, FundTypeResponseBuilder
# from apps.tcc.usecase.repo.domain_repo.donations import DonationRepository, FundRepository
# from usecases.base.base_uc import BaseUseCase
# from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
# from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
# from apps.tcc.usecase.domain_exception.d_exceptions import (
#     DonationException,
#     DonationAmountInvalidException,
#     FundInactiveException,
#     DonationPaymentFailedException
# )
# # Import Schemas and Response Builder
# from apps.core.schemas.schemas.donations import DonationCreateSchema, FundTypeCreateSchema


# class CreateDonationUseCase(BaseUseCase):
#     """Use case for creating new donations"""
    
#     def __init__(self, donation_repository: DonationRepository,fund_repository: FundRepository):
#         super().__init__()
#         self.donation_repository = donation_repository
#         self.fund_repository = fund_repository
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         # Validate input against DonationCreateSchema
#         try:
#             # Note: user_id is dummy for schema validation if not already in input_data
#             DonationCreateSchema(**input_data, user_id=1)
#         except Exception as e:
#              raise DonationException(
#                 message="Input validation failed",
#                 error_code="INVALID_INPUT",
#                 details={"schema_error": str(e)},
#                 user_message="Invalid data provided for donation creation."
#             )
            
#         # Also include existing custom validation checks (if necessary, though schema should cover most)
        
#         # Validate amount (if needed outside schema validation range)
#         amount = input_data.get('amount')
#         if amount:
#             await self._validate_amount(amount)
        
#         # Validate payment method
#         payment_method = input_data.get('payment_method')
#         if payment_method:
#             await self._validate_payment_method(payment_method)

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         # Validate fund if provided
#         if input_data.get('fund_id'):
#             await self._validate_fund(input_data['fund_id'])
        
#         # Convert input to DonationEntity
#         donation_entity = DonationEntity(donation_data=DonationCreateSchema(**input_data))
#         # Create donation using repository
#         created_donation = await self.donation_repository.create(donation_entity)
        
#         return {
#             "message": "Donation created successfully",
#             "donation": DonationResponseBuilder.to_response(created_donation).model_dump()
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

#     async def _validate_payment_method(self, payment_method: str) -> None:
#         """Validate payment method"""
#         valid_methods = [method.value for method in PaymentMethod]
        
#         if payment_method not in valid_methods:
#             raise DonationException(
#                 message=f"Invalid payment method: {payment_method}",
#                 error_code="INVALID_PAYMENT_METHOD",
#                 details={"valid_methods": valid_methods},
#                 user_message=f"Payment method '{payment_method}' is not supported. Valid methods: {', '.join(valid_methods)}"
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


# class CreateFundTypeUseCase(BaseUseCase):
#     """Use case for creating new fund types"""
    
#     def __init__(self):
#         super().__init__()
#         self.fund_repository = FundRepository()
    
#     def _setup_configuration(self):
#         self.config.require_authentication = True
#         self.config.required_permissions = ['can_manage_donations']

#     async def _validate_input(self, input_data: Dict[str, Any], context):
#         # Validate input against FundTypeCreateSchema
#         try:
#             FundTypeCreateSchema(**input_data)
#         except Exception as e:
#              raise DonationException(
#                 message="Input validation failed",
#                 error_code="INVALID_INPUT",
#                 details={"schema_error": str(e)},
#                 user_message="Invalid data provided for fund type creation."
#             )

#     async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
#         # Convert input to FundTypeEntity
#         fund_entity = FundTypeEntity(
#             name=input_data['name'],
#             description=input_data['description'],
#             target_amount=Decimal(str(input_data['target_amount'])) if input_data.get('target_amount') else None,
#             current_amount=Decimal(str(input_data.get('current_balance', 0))),
#             is_active=input_data.get('is_active', True)
#         )
        
#         # Create fund type using repository
#         created_fund = await self.fund_repository.create(fund_entity)
        
#         return {
#             "message": "Fund type created successfully",
#             "fund": FundTypeResponseBuilder.to_response(created_fund).model_dump()
#         }