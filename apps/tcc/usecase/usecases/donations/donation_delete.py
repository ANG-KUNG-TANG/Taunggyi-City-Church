from typing import Dict, Any
from apps.tcc.models.base.enums import DonationStatus
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.d_exceptions import (
    DonationException,
    DonationNotFoundException
)


class DeleteDonationUseCase(BaseUseCase):
    """Use case for soft deleting donations"""
    
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
        
        # Verify donation exists
        existing_donation = await self.donation_repository.get_by_id(donation_id, user)
        if not existing_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        # Soft delete donation
        result = await self.donation_repository.delete(donation_id, user)
        
        if not result:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found for deletion."
            )
        
        return {
            "message": "Donation deleted successfully",
            "donation_id": donation_id
        }


class DeleteFundTypeUseCase(BaseUseCase):
    """Use case for soft deleting fund types"""
    
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
        
        # Verify fund exists
        existing_fund = await self.fund_repository.get_by_id(fund_id, user)
        if not existing_fund:
            raise DonationException(
                message=f"Fund {fund_id} not found",
                error_code="FUND_NOT_FOUND",
                user_message="Fund not found."
            )
        
        # Check if fund has donations
        donations = await self.donation_repository.get_donations_by_fund(fund_id, user)
        if donations:
            raise DonationException(
                message="Cannot delete fund with existing donations",
                error_code="FUND_HAS_DONATIONS",
                user_message="Cannot delete fund that has existing donations. Please reassign donations first."
            )
        
        # Soft delete fund type
        result = await self.fund_repository.delete(fund_id, user)
        
        if not result:
            raise DonationException(
                message=f"Fund {fund_id} not found for deletion",
                error_code="FUND_DELETION_FAILED",
                user_message="Fund not found for deletion."
            )
        
        return {
            "message": "Fund type deleted successfully",
            "fund_id": fund_id
        }


class CancelDonationUseCase(BaseUseCase):
    """Use case for canceling donations"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

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
        
        # Verify donation exists and belongs to user
        existing_donation = await self.donation_repository.get_by_id(donation_id, user)
        if not existing_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        # Check if user owns the donation or has permission
        if existing_donation.donor_id != user.id and not user.can_manage_donations:
            raise DonationException(
                message="You can only cancel your own donations",
                error_code="PERMISSION_DENIED",
                user_message="You can only cancel your own donations."
            )
        
        # Update status to cancelled
        update_data = {'status': DonationStatus.CANCELLED}
        updated_donation = await self.donation_repository.update(donation_id, update_data, user)
        
        if not updated_donation:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found for cancellation."
            )
        
        return {
            "message": "Donation cancelled successfully",
            "donation_id": donation_id
        }