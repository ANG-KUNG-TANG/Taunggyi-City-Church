from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal
from asgiref.sync import sync_to_async
from repo.base.modelrepo import DomainRepository  # Changed from ModelRepository
from apps.tcc.models.donations.donation import Donation, FundType
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from entities.donations import DonationEntity, FundTypeEntity  # Add entity imports
from models.base.permission import PermissionDenied
from core.db.decorators import with_db_error_handling, with_retry


class DonationRepository(DomainRepository):  # Changed base class
    
    def __init__(self):
        super().__init__(Donation)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, data, user, request=None) -> DonationEntity:
        """Create a new donation"""
        donation = await sync_to_async(super().create)(data, user, request)
        return await self._model_to_entity(donation)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, object_id, user, *args, **kwargs) -> Optional[DonationEntity]:
        """Get donation by ID with permission check"""
        donation = await sync_to_async(super().get_by_id)(object_id, user, *args, **kwargs)
        if not donation:
            return None
        return await self._model_to_entity(donation)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, object_id, data, user, request=None) -> Optional[DonationEntity]:
        """Update an existing donation"""
        donation = await sync_to_async(super().update)(object_id, data, user, request)
        if not donation:
            return None
        return await self._model_to_entity(donation)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, object_id, user, request=None) -> bool:
        """Soft delete a donation"""
        return await sync_to_async(super().delete)(object_id, user, request)

    # ... rest of your existing methods ...
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, donation_model: Donation) -> DonationEntity:
        """Convert Django model to DonationEntity"""
        return DonationEntity(
            id=donation_model.id,
            donor_id=donation_model.donor.id,
            fund_id=donation_model.fund.id if donation_model.fund else None,
            amount=donation_model.amount,
            payment_method=donation_model.payment_method,
            status=donation_model.status,
            donation_date=donation_model.donation_date,
            transaction_id=donation_model.transaction_id,
            is_recurring=donation_model.is_recurring,
            is_active=donation_model.is_active,
            created_at=donation_model.created_at,
            updated_at=donation_model.updated_at
        )


class FundTypeRepository(DomainRepository):  # Changed base class
    
    def __init__(self):
        super().__init__(FundType)
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def create(self, data, user, request=None) -> FundTypeEntity:
        """Create a new fund type"""
        fund = await sync_to_async(super().create)(data, user, request)
        return await self._model_to_entity(fund)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, object_id, user, *args, **kwargs) -> Optional[FundTypeEntity]:
        """Get fund type by ID with permission check"""
        fund = await sync_to_async(super().get_by_id)(object_id, user, *args, **kwargs)
        if not fund:
            return None
        return await self._model_to_entity(fund)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def update(self, object_id, data, user, request=None) -> Optional[FundTypeEntity]:
        """Update an existing fund type"""
        fund = await sync_to_async(super().update)(object_id, data, user, request)
        if not fund:
            return None
        return await self._model_to_entity(fund)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def delete(self, object_id, user, request=None) -> bool:
        """Soft delete a fund type"""
        return await sync_to_async(super().delete)(object_id, user, request)

    # ... rest of your existing methods ...
    
    # ============ CONVERSION METHODS ============
    
    async def _model_to_entity(self, fund_model: FundType) -> FundTypeEntity:
        """Convert Django model to FundTypeEntity"""
        return FundTypeEntity(
            id=fund_model.id,
            name=fund_model.name,
            description=fund_model.description,
            target_amount=fund_model.target_amount,
            current_amount=fund_model.current_amount,
            is_active=fund_model.is_active,
            created_at=fund_model.created_at,
            updated_at=fund_model.updated_at
        )