from typing import Dict, Any
from decimal import Decimal
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
from apps.tcc.models.base.enums import DonationStatus
from apps.tcc.usecase.domain_exception.d_exceptions import (
    DonationException,
    DonationNotFoundException,
    DonationAmountInvalidException,
    FundInactiveException
)


class UpdateDonationUseCase(BaseUseCase):
    """Use case for updating donations"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        donation_id = input_data.get('donation_id')
        if not donation_id:
            raise DonationException(
                message="Donation ID is required",
                error_code="MISSING_DONATION_ID",
                user_message="Donation ID is required."
            )
        
        # Validate amount if provided
        amount = input_data.get('amount')
        if amount:
            await self._validate_amount(amount)

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        donation_id = input_data['donation_id']
        
        # Check if donation exists
        existing_donation = await self.donation_repository.get_by_id(donation_id, user)
        if not existing_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        # Validate fund if being updated
        if 'fund_id' in input_data and input_data['fund_id']:
            await self._validate_fund(input_data['fund_id'], user)
        
        # Prepare update data
        update_data = {
            'amount': input_data.get('amount', existing_donation.amount),
            'status': input_data.get('status', existing_donation.status),
            'fund_id': input_data.get('fund_id', existing_donation.fund_id),
            'notes': input_data.get('notes', getattr(existing_donation, 'notes', ''))
        }
        
        # Update donation
        updated_donation = await self.donation_repository.update(donation_id, update_data, user)
        
        if not updated_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found for update."
            )
        
        return {
            "message": "Donation updated successfully",
            "donation": self._format_donation_response(updated_donation)
        }

    async def _validate_amount(self, amount: float) -> None:
        """Validate donation amount"""
        min_amount = Decimal('0.01')
        max_amount = Decimal('100000.00')
        
        if amount < min_amount or amount > max_amount:
            raise DonationAmountInvalidException(
                amount=amount,
                min_amount=float(min_amount),
                max_amount=float(max_amount),
                user_message=f"Donation amount must be between ${min_amount:.2f} and ${max_amount:.2f}."
            )

    async def _validate_fund(self, fund_id: int, user: Any) -> None:
        """Validate fund is active"""
        fund_entity = await self.fund_repository.get_by_id(fund_id, user)
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


class UpdateFundTypeUseCase(BaseUseCase):
    """Use case for updating fund types"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        fund_id = input_data.get('fund_id')
        if not fund_id:
            raise DonationException(
                message="Fund ID is required",
                error_code="MISSING_FUND_ID",
                user_message="Fund ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        fund_id = input_data['fund_id']
        
        # Check if fund exists
        existing_fund = await self.fund_repository.get_by_id(fund_id, user)
        if not existing_fund:
            raise DonationException(
                message=f"Fund {fund_id} not found",
                error_code="FUND_NOT_FOUND",
                user_message="Fund not found."
            )
        
        # Prepare update data
        update_data = {
            'name': input_data.get('name', existing_fund.name),
            'description': input_data.get('description', existing_fund.description),
            'target_amount': input_data.get('target_amount', existing_fund.target_amount),
            'current_amount': input_data.get('current_amount', existing_fund.current_amount),
            'is_active': input_data.get('is_active', existing_fund.is_active)
        }
        
        # Update fund type
        updated_fund = await self.fund_repository.update(fund_id, update_data, user)
        
        if not updated_fund:
            raise DonationException(
                message=f"Fund {fund_id} not found for update",
                error_code="FUND_UPDATE_FAILED",
                user_message="Fund not found for update."
            )
        
        return {
            "message": "Fund type updated successfully",
            "fund": self._format_fund_response(updated_fund)
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


class UpdateDonationStatusUseCase(BaseUseCase):
    """Use case for updating donation status"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        donation_id = input_data.get('donation_id')
        status = input_data.get('status')
        
        if not donation_id:
            raise DonationException(
                message="Donation ID is required",
                error_code="MISSING_DONATION_ID",
                user_message="Donation ID is required."
            )
        
        if not status:
            raise DonationException(
                message="Status is required",
                error_code="MISSING_STATUS",
                user_message="Donation status is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        donation_id = input_data['donation_id']
        status = input_data['status']
        
        # Check if donation exists
        existing_donation = await self.donation_repository.get_by_id(donation_id, user)
        if not existing_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        # Update status
        update_data = {'status': status}
        updated_donation = await self.donation_repository.update(donation_id, update_data, user)
        
        if not updated_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found for status update."
            )
        
        return {
            "message": "Donation status updated successfully",
            "donation": self._format_donation_response(updated_donation)
        }

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


class ProcessDonationPaymentUseCase(BaseUseCase):
    """Use case for processing donation payments"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        donation_id = input_data.get('donation_id')
        if not donation_id:
            raise DonationException(
                message="Donation ID is required",
                error_code="MISSING_DONATION_ID",
                user_message="Donation ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        donation_id = input_data['donation_id']
        transaction_id = input_data.get('transaction_id')
        
        # Check if donation exists
        existing_donation = await self.donation_repository.get_by_id(donation_id, user)
        if not existing_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        # Process payment (this would integrate with actual payment gateway)
        # For now, we'll simulate successful payment
        update_data = {
            'status': DonationStatus.COMPLETED,
            'transaction_id': transaction_id
        }
        
        updated_donation = await self.donation_repository.update(donation_id, update_data, user)
        
        if not updated_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found for payment processing."
            )
        
        # Update fund current amount if fund is specified
        if updated_donation.fund_id and updated_donation.status == DonationStatus.COMPLETED:
            await self._update_fund_amount(updated_donation.fund_id, updated_donation.amount, user)
        
        return {
            "message": "Donation payment processed successfully",
            "donation": self._format_donation_response(updated_donation)
        }

    async def _update_fund_amount(self, fund_id: int, amount: Decimal, user: Any) -> None:
        """Update fund current amount"""
        fund_entity = await self.fund_repository.get_by_id(fund_id, user)
        if fund_entity:
            new_amount = (fund_entity.current_amount or Decimal('0')) + amount
            await self.fund_repository.update(fund_id, {'current_amount': new_amount}, user)

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