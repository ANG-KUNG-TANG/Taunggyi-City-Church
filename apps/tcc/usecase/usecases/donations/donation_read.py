from typing import Dict, Any, List, Optional
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from apps.tcc.usecase.domain_exception.d_exceptions import (
    DonationException,
    DonationNotFoundException
)


class GetDonationByIdUseCase(BaseUseCase):
    """Use case for getting donation by ID"""
    
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
        donation_entity = await self.donation_repository.get_by_id(donation_id, user)
        
        if not donation_entity:
            raise DonationNotFoundException(
                donation_id=str(donation_id),
                user_message="Donation not found."
            )
        
        return {
            "donation": self._format_donation_response(donation_entity)
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


class GetAllDonationsUseCase(BaseUseCase):
    """Use case for getting all donations with optional filtering"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        donations = await self.donation_repository.get_all(user, filters)
        
        return {
            "donations": [self._format_donation_response(donation) for donation in donations],
            "total_count": len(donations)
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


class GetUserDonationsUseCase(BaseUseCase):
    """Use case for getting all donations by a user"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        donations = await self.donation_repository.get_user_donations(user)
        
        return {
            "donations": [self._format_donation_response(donation) for donation in donations],
            "total_count": len(donations)
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


class GetDonationsByStatusUseCase(BaseUseCase):
    """Use case for getting donations by status"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _validate_input(self, input_data: Dict[str, Any], context):
        status = input_data.get('status')
        if not status:
            raise DonationException(
                message="Status is required",
                error_code="MISSING_STATUS",
                user_message="Donation status is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        status = input_data['status']
        donations = await self.donation_repository.get_donations_by_status(status, user)
        
        return {
            "donations": [self._format_donation_response(donation) for donation in donations],
            "status": status.value if hasattr(status, 'value') else status,
            "total_count": len(donations)
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


class GetFundTypeByIdUseCase(BaseUseCase):
    """Use case for getting fund type by ID"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

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
        fund_entity = await self.fund_repository.get_by_id(fund_id, user)
        
        if not fund_entity:
            raise DonationException(
                message=f"Fund {fund_id} not found",
                error_code="FUND_NOT_FOUND",
                user_message="Fund not found."
            )
        
        return {
            "fund": self._format_fund_response(fund_entity)
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


class GetAllFundTypesUseCase(BaseUseCase):
    """Use case for getting all fund types"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        funds = await self.fund_repository.get_all(user, filters)
        
        return {
            "funds": [self._format_fund_response(fund) for fund in funds],
            "total_count": len(funds)
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


class GetActiveFundTypesUseCase(BaseUseCase):
    """Use case for getting active fund types"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        funds = await self.fund_repository.get_active_funds(user)
        
        return {
            "funds": [self._format_fund_response(fund) for fund in funds],
            "total_count": len(funds)
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


class GetDonationsByFundUseCase(BaseUseCase):
    """Use case for getting donations by fund"""
    
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
        donations = await self.donation_repository.get_donations_by_fund(fund_id, user)
        
        return {
            "fund_id": fund_id,
            "donations": [self._format_donation_response(donation) for donation in donations],
            "total_count": len(donations)
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


class GetDonationStatsUseCase(BaseUseCase):
    """Use case for getting donation statistics"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True
        self.config.required_permissions = ['can_manage_donations']

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        stats = await self.donation_repository.get_donation_stats(user)
        
        return {
            "statistics": stats
        }