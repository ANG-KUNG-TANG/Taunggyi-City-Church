from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal
from asgiref.sync import sync_to_async
from apps.core.cache.async_cache import AsyncCache
from repo.base.modelrepo import DomainRepository
from apps.tcc.models.donations.donation import Donation, FundType
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from entities.donations import DonationEntity, FundTypeEntity
from core.db.decorators import with_db_error_handling, with_retry
from utils.audit_logging import AuditLogger
from core.cache.decorator import cached, cache_invalidate
import logging

logger = logging.getLogger(__name__)

class DonationRepository(DomainRepository):
    
    def __init__(self, cache: AsyncCache = None):
        super().__init__(Donation)
        self.cache = cache
    
    # ============ CRUD OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=[
            "donation:{donation_entity.id}",
            "donations:total",
            "donations:recent",
            "donations:stats"
        ],
        namespace="donations",
        version="1"
    )
    async def create(self, data) -> DonationEntity:
        """Create a new donation with audit logging"""
        donation = await sync_to_async(super().create)(data)
        donation_entity = await self._model_to_entity(donation)
        
        # Audit logging
        await AuditLogger.log_create(
            user=None,
            obj=donation,
            notes=f"Created donation: {donation_entity.id} for amount {donation_entity.amount}",
            ip_address="system",
            user_agent="system"
        )
        
        logger.info(f"Donation created successfully: {donation_entity.id}")
        return donation_entity
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="donation:{object_id}",
        ttl=1800,  # 30 minutes
        namespace="donations",
        version="1"
    )
    async def get_by_id(self, object_id, *args, **kwargs) -> Optional[DonationEntity]:
        """Get donation by ID with caching"""
        donation = await sync_to_async(super().get_by_id)(object_id, *args, **kwargs)
        if not donation:
            return None
        return await self._model_to_entity(donation)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=[
            "donation:{object_id}",
            "donations:total",
            "donations:recent",
            "donations:stats"
        ],
        namespace="donations",
        version="1"
    )
    async def update(self, object_id, data) -> Optional[DonationEntity]:
        """Update an existing donation with audit logging"""
        old_donation = await self._get_by_id_uncached(object_id)
        
        donation = await sync_to_async(super().update)(object_id, data)
        if not donation:
            return None
        
        donation_entity = await self._model_to_entity(donation)
        
        # Audit logging
        changes = {
            'status': {'old': old_donation.status, 'new': donation_entity.status},
            'amount': {'old': old_donation.amount, 'new': donation_entity.amount}
        }
        await AuditLogger.log_update(
            user=None,
            obj=donation,
            changes=changes,
            notes=f"Updated donation: {donation_entity.id}",
            ip_address="system",
            user_agent="system"
        )
        
        logger.info(f"Donation updated successfully: {donation_entity.id}")
        return donation_entity
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cache_invalidate(
        key_templates=[
            "donation:{object_id}",
            "donations:total",
            "donations:recent",
            "donations:stats"
        ],
        namespace="donations",
        version="1"
    )
    async def delete(self, object_id) -> bool:
        """Soft delete a donation with audit logging"""
        donation = await self._get_by_id_uncached(object_id)
        if not donation:
            return False
        
        # Audit logging
        await AuditLogger.log_delete(
            user=None,
            obj=donation,
            notes=f"Deleted donation: {donation.id}",
            ip_address="system",
            user_agent="system"
        )
        
        result = await sync_to_async(super().delete)(object_id)
        
        if result:
            logger.info(f"Donation deleted successfully: {donation.id}")
        
        return result

    # ============ ANALYTICS OPERATIONS ============
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="donations:total",
        ttl=300,  # 5 minutes
        namespace="donations",
        version="1"
    )
    async def get_total_donations(self) -> Decimal:
        """Get total donations amount with caching"""
        result = await Donation.objects.filter(
            is_active=True,
            status=DonationStatus.COMPLETED
        ).aggregate(total=Sum('amount'))
        
        return result['total'] or Decimal('0')
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    @cached(
        key_template="donations:recent:{limit}",
        ttl=600,  # 10 minutes
        namespace="donations",
        version="1"
    )
    async def get_recent_donations(self, limit: int = 10) -> List[DonationEntity]:
        """Get recent donations with caching"""
        # Add limit for decorator
        setattr(self, 'limit', limit)
        
        donations = []
        async for donation in Donation.objects.filter(
            is_active=True
        ).order_by('-donation_date')[:limit]:
            donations.append(await self._model_to_entity(donation))
        return donations
    
    # ============ INTERNAL METHODS ============
    
    async def _get_by_id_uncached(self, object_id) -> Optional[DonationEntity]:
        """Internal method to get donation by ID without cache"""
        donation = await sync_to_async(super().get_by_id)(object_id)
        if not donation:
            return None
        return await self._model_to_entity(donation)
    
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