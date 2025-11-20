from typing import Dict, Any
from decimal import Decimal
from apps.tcc.usecase.repo.domain_repo.donations import DonationRepository, FundRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from apps.tcc.usecase.domain_exception.d_exceptions import (
    DonationException,
    DonationAmountInvalidException,
    FundInactiveException,
    DonationPaymentFailedException
)


class CreateDonationUseCase(BaseUseCase):
    """Use case for creating new donations"""
    
    def __init__(self):
        super().__init__()
        self.donation_repository = DonationRepository()
        self.fund_repository = FundRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['amount', 'payment_method']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise DonationException(
                message="Missing required fields",
                error_code="MISSING_REQUIRED_FIELDS",
                details={"missing_fields": missing_fields},
                user_message="Please provide all required fields: amount and payment method."
            )
        
        # Validate amount
        amount = input_data.get('amount')
        if amount:
            await self._validate_amount(amount)
        
        # Validate payment method
        payment_method = input_data.get('payment_method')
        if payment_method:
            await self._validate_payment_method(payment_method)

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Validate fund if provided
        if input_data.get('fund_id'):
            await self._validate_fund(input_data['fund_id'])
        
        # Convert input to DonationEntity
        donation_entity = DonationEntity(
            donor_id=user.id,
            fund_id=input_data.get('fund_id'),
            amount=Decimal(str(input_data['amount'])),
            payment_method=input_data['payment_method'],
            status=DonationStatus.PENDING,
            donation_date=input_data.get('donation_date'),
            transaction_id=input_data.get('transaction_id'),
            is_recurring=input_data.get('is_recurring', False),
            is_active=True
        )
        
        # Create donation using repository
        created_donation = await self.donation_repository.create(donation_entity)
        
        return {
            "message": "Donation created successfully",
            "donation": self._format_donation_response(created_donation)
        }

    async def _validate_amount(self, amount: float) -> None:
        """Validate donation amount"""
        min_amount = Decimal('0.01')
        max_amount = Decimal('100000.00')
        amount_decimal = Decimal(str(amount))
        
        if amount_decimal < min_amount or amount_decimal > max_amount:
            raise DonationAmountInvalidException(
                amount=amount,
                min_amount=float(min_amount),
                max_amount=float(max_amount),
                user_message=f"Donation amount must be between ${min_amount:.2f} and ${max_amount:.2f}."
            )

    async def _validate_payment_method(self, payment_method: str) -> None:
        """Validate payment method"""
        valid_methods = [method.value for method in PaymentMethod]
        
        if payment_method not in valid_methods:
            raise DonationException(
                message=f"Invalid payment method: {payment_method}",
                error_code="INVALID_PAYMENT_METHOD",
                details={"valid_methods": valid_methods},
                user_message=f"Payment method '{payment_method}' is not supported. Valid methods: {', '.join(valid_methods)}"
            )

    async def _validate_fund(self, fund_id: int) -> None:
        """Validate fund is active"""
        fund_entity = await self.fund_repository.get_by_id(fund_id)
        if not fund_entity:
            raise DonationException(
                message=f"Fund {fund_id} not found",
                error_code="FUND_NOT_FOUND",
                user_message="Selected fund not found."
            )
        
        if not fund_entity.is_active:
            raise FundInactiveException(
                fund_id=str(fund_id),
                fund_name=fund_entity.name,
                user_message=f"Fund '{fund_entity.name}' is not currently accepting donations."
            )

    @staticmethod
    def _format_donation_response(donation_entity: DonationEntity) -> Dict[str, Any]:
        """Format donation entity for response"""
        return {
            'id': donation_entity.id,
            'donor_id': donation_entity.donor_id,
            'fund_id': donation_entity.fund_id,
            'amount': float(donation_entity.amount) if donation_entity.amount else None,
            'payment_method': donation_entity.payment_method.value if hasattr(donation_entity.payment_method, 'value') else donation_entity.payment_method,
            'status': donation_entity.status.value if hasattr(donation_entity.status, 'value') else donation_entity.status,
            'donation_date': donation_entity.donation_date,
            'transaction_id': donation_entity.transaction_id,
            'is_recurring': donation_entity.is_recurring,
            'is_active': donation_entity.is_active,
            'created_at': donation_entity.created_at,
            'updated_at': donation_entity.updated_at
        }


class CreateFundTypeUseCase(BaseUseCase):
    """Use case for creating new fund types"""
    
    def __init__(self):
        super().__init__()
        self.fund_repository = FundRepository()
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['name', 'description']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise DonationException(
                message="Missing required fields",
                error_code="MISSING_REQUIRED_FIELDS",
                details={"missing_fields": missing_fields},
                user_message="Please provide all required fields: name and description."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Convert input to FundTypeEntity
        fund_entity = FundTypeEntity(
            name=input_data['name'],
            description=input_data['description'],
            target_amount=Decimal(str(input_data['target_amount'])) if input_data.get('target_amount') else None,
            current_amount=Decimal(str(input_data.get('current_amount', 0))),
            is_active=input_data.get('is_active', True)
        )
        
        # Create fund type using repository
        created_fund = await self.fund_repository.create(fund_entity)
        
        return {
            "message": "Fund type created successfully",
            "fund": self._format_fund_response(created_fund)
        }

    @staticmethod
    def _format_fund_response(fund_entity: FundTypeEntity) -> Dict[str, Any]:
        """Format fund entity for response"""
        return {
            'id': fund_entity.id,
            'name': fund_entity.name,
            'description': fund_entity.description,
            'target_amount': float(fund_entity.target_amount) if fund_entity.target_amount else None,
            'current_amount': float(fund_entity.current_amount) if fund_entity.current_amount else None,
            'is_active': fund_entity.is_active,
            'created_at': fund_entity.created_at,
            'updated_at': fund_entity.updated_at
        }