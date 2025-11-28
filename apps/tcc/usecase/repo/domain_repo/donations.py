# from typing import List, Optional, Dict, Any
# from django.utils import timezone
# from django.db.models import Q, Sum
# from decimal import Decimal
# from asgiref.sync import sync_to_async
# from apps.core.cache.async_cache import AsyncCache
# from apps.tcc.usecase.repo.base.modelrepo import DomainRepository  
# from apps.tcc.models.donations.donation import Donation, FundType
# from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
# from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity
# from core.db.decorators import with_db_error_handling, with_retry
# from utils.audit_logging import AuditLogger
# from core.cache.decorator import cached, cache_invalidate
# import logging

# logger = logging.getLogger(__name__)

# class DonationRepository(DomainRepository):
    
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(Donation)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "donation:{donation_entity.id}",
#             "donations:total",
#             "donations:recent",
#             "donations:stats",
#             "donations:user:{donation_entity.donor_id}"
#         ],
#         namespace="donations",
#         version="1"
#     )
#     async def create(self, donation_entity: DonationEntity) -> DonationEntity:
#         """Create a new donation with audit logging"""
#         donation_data = {
#             'donor_id': donation_entity.donor_id,
#             'fund_id': donation_entity.fund_id,
#             'amount': donation_entity.amount,
#             'payment_method': donation_entity.payment_method,
#             'status': donation_entity.status,
#             'donation_date': donation_entity.donation_date,
#             'transaction_id': donation_entity.transaction_id,
#             'is_recurring': donation_entity.is_recurring,
#             'is_active': donation_entity.is_active
#         }
        
#         donation = await sync_to_async(super().create)(donation_data)
#         created_entity = await self._model_to_entity(donation)
        
#         # Audit logging
#         await AuditLogger.log_create(
#             user=None,
#             obj=donation,
#             notes=f"Created donation: {created_entity.id} for amount {created_entity.amount}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Donation created successfully: {created_entity.id}")
#         return created_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donation:{object_id}",
#         ttl=1800,  # 30 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_by_id(self, object_id: int) -> Optional[DonationEntity]:
#         """Get donation by ID with caching"""
#         donation = await sync_to_async(super().get_by_id)(object_id)
#         if not donation:
#             return None
#         return await self._model_to_entity(donation)
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "donation:{object_id}",
#             "donations:total",
#             "donations:recent",
#             "donations:stats",
#             "donations:user:{donation_entity.donor_id}"
#         ],
#         namespace="donations",
#         version="1"
#     )
#     async def update(self, object_id: int, donation_entity: DonationEntity) -> Optional[DonationEntity]:
#         """Update an existing donation with audit logging"""
#         old_donation = await self._get_by_id_uncached(object_id)
        
#         update_data = {
#             'fund_id': donation_entity.fund_id,
#             'amount': donation_entity.amount,
#             'payment_method': donation_entity.payment_method,
#             'status': donation_entity.status,
#             'donation_date': donation_entity.donation_date,
#             'transaction_id': donation_entity.transaction_id,
#             'is_recurring': donation_entity.is_recurring,
#             'is_active': donation_entity.is_active
#         }
        
#         donation = await sync_to_async(super().update)(object_id, update_data)
#         if not donation:
#             return None
        
#         updated_entity = await self._model_to_entity(donation)
        
#         # Audit logging
#         changes = {
#             'status': {'old': old_donation.status, 'new': updated_entity.status},
#             'amount': {'old': old_donation.amount, 'new': updated_entity.amount}
#         }
#         await AuditLogger.log_update(
#             user=None,
#             obj=donation,
#             changes=changes,
#             notes=f"Updated donation: {updated_entity.id}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Donation updated successfully: {updated_entity.id}")
#         return updated_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "donation:{object_id}",
#             "donations:total",
#             "donations:recent",
#             "donations:stats"
#         ],
#         namespace="donations",
#         version="1"
#     )
#     async def delete(self, object_id: int) -> bool:
#         """Soft delete a donation with audit logging"""
#         donation = await self._get_by_id_uncached(object_id)
#         if not donation:
#             return False
        
#         # Audit logging
#         await AuditLogger.log_delete(
#             user=None,
#             obj=donation,
#             notes=f"Deleted donation: {donation.id}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         result = await sync_to_async(super().delete)(object_id)
        
#         if result:
#             logger.info(f"Donation deleted successfully: {donation.id}")
        
#         return result

#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:all:{filters}",
#         ttl=300,  # 5 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_all(self, filters: Dict[str, Any] = None) -> List[DonationEntity]:
#         """Get all donations with optional filtering"""
#         queryset = Donation.objects.filter(is_active=True)
        
#         if filters:
#             if 'status' in filters:
#                 queryset = queryset.filter(status=filters['status'])
#             if 'donor_id' in filters:
#                 queryset = queryset.filter(donor_id=filters['donor_id'])
#             if 'fund_id' in filters:
#                 queryset = queryset.filter(fund_id=filters['fund_id'])
#             if 'payment_method' in filters:
#                 queryset = queryset.filter(payment_method=filters['payment_method'])
        
#         donations = []
#         async for donation in queryset:
#             donations.append(await self._model_to_entity(donation))
#         return donations
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:user:{user_id}",
#         ttl=600,  # 10 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_user_donations(self, user_id: int) -> List[DonationEntity]:
#         """Get all donations by a specific user"""
#         donations = []
#         async for donation in Donation.objects.filter(donor_id=user_id, is_active=True):
#             donations.append(await self._model_to_entity(donation))
#         return donations
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:status:{status}",
#         ttl=300,  # 5 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_donations_by_status(self, status: DonationStatus) -> List[DonationEntity]:
#         """Get donations by status"""
#         donations = []
#         async for donation in Donation.objects.filter(status=status, is_active=True):
#             donations.append(await self._model_to_entity(donation))
#         return donations
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:fund:{fund_id}",
#         ttl=300,  # 5 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_donations_by_fund(self, fund_id: int) -> List[DonationEntity]:
#         """Get donations by fund"""
#         donations = []
#         async for donation in Donation.objects.filter(fund_id=fund_id, is_active=True):
#             donations.append(await self._model_to_entity(donation))
#         return donations

#     # ============ ANALYTICS OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:total",
#         ttl=300,  # 5 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_total_donations(self) -> Decimal:
#         """Get total donations amount with caching"""
#         result = await sync_to_async(lambda: Donation.objects.filter(
#             is_active=True,
#             status=DonationStatus.COMPLETED
#         ).aggregate(total=Sum('amount')))()
        
#         return result['total'] or Decimal('0')
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:recent:{limit}",
#         ttl=600,  # 10 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_recent_donations(self, limit: int = 10) -> List[DonationEntity]:
#         """Get recent donations with caching"""
#         donations = []
#         async for donation in Donation.objects.filter(
#             is_active=True
#         ).order_by('-donation_date')[:limit]:
#             donations.append(await self._model_to_entity(donation))
#         return donations
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="donations:stats",
#         ttl=300,  # 5 minutes
#         namespace="donations",
#         version="1"
#     )
#     async def get_donation_stats(self) -> Dict[str, Any]:
#         """Get donation statistics"""
#         total_amount = await self.get_total_donations()
#         recent_donations = await self.get_recent_donations(5)
        
#         # Get count by status
#         status_counts = {}
#         for status in DonationStatus:
#             count = await sync_to_async(lambda s: Donation.objects.filter(
#                 status=s, is_active=True
#             ).count())(status)
#             status_counts[status.value] = count
        
#         return {
#             'total_amount': float(total_amount),
#             'total_donations': await sync_to_async(lambda: Donation.objects.filter(is_active=True).count())(),
#             'recent_donations_count': len(recent_donations),
#             'status_breakdown': status_counts
#         }
    
#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, object_id: int) -> Optional[DonationEntity]:
#         """Internal method to get donation by ID without cache"""
#         donation = await sync_to_async(super().get_by_id)(object_id)
#         if not donation:
#             return None
#         return await self._model_to_entity(donation)
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, donation_model: Donation) -> DonationEntity:
#         """Convert Django model to DonationEntity"""
#         return DonationEntity(
#             id=donation_model.id,
#             donor_id=donation_model.donor.id,
#             fund_id=donation_model.fund.id if donation_model.fund else None,
#             amount=donation_model.amount,
#             payment_method=donation_model.payment_method,
#             status=donation_model.status,
#             donation_date=donation_model.donation_date,
#             transaction_id=donation_model.transaction_id,
#             is_recurring=donation_model.is_recurring,
#             is_active=donation_model.is_active,
#             created_at=donation_model.created_at,
#             updated_at=donation_model.updated_at
#         )


# class FundRepository(DomainRepository):
#     """Repository for FundType operations"""
    
#     def __init__(self, cache: AsyncCache = None):
#         super().__init__(FundType)
#         self.cache = cache
    
#     # ============ CRUD OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "fund:{fund_entity.id}",
#             "funds:all",
#             "funds:active"
#         ],
#         namespace="funds",
#         version="1"
#     )
#     async def create(self, fund_entity: FundTypeEntity) -> FundTypeEntity:
#         """Create a new fund type with audit logging"""
#         fund_data = {
#             'name': fund_entity.name,
#             'description': fund_entity.description,
#             'target_amount': fund_entity.target_amount,
#             'current_amount': fund_entity.current_amount,
#             'is_active': fund_entity.is_active
#         }
        
#         fund = await sync_to_async(super().create)(fund_data)
#         created_entity = await self._model_to_entity(fund)
        
#         # Audit logging
#         await AuditLogger.log_create(
#             user=None,
#             obj=fund,
#             notes=f"Created fund type: {created_entity.id} - {created_entity.name}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Fund type created successfully: {created_entity.id}")
#         return created_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="fund:{object_id}",
#         ttl=1800,  # 30 minutes
#         namespace="funds",
#         version="1"
#     )
#     async def get_by_id(self, object_id: int) -> Optional[FundTypeEntity]:
#         """Get fund type by ID with caching"""
#         fund = await sync_to_async(super().get_by_id)(object_id)
#         if not fund:
#             return None
#         return await self._model_to_entity(fund)
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "fund:{object_id}",
#             "funds:all",
#             "funds:active"
#         ],
#         namespace="funds",
#         version="1"
#     )
#     async def update(self, object_id: int, fund_entity: FundTypeEntity) -> Optional[FundTypeEntity]:
#         """Update an existing fund type with audit logging"""
#         old_fund = await self._get_by_id_uncached(object_id)
        
#         update_data = {
#             'name': fund_entity.name,
#             'description': fund_entity.description,
#             'target_amount': fund_entity.target_amount,
#             'current_amount': fund_entity.current_amount,
#             'is_active': fund_entity.is_active
#         }
        
#         fund = await sync_to_async(super().update)(object_id, update_data)
#         if not fund:
#             return None
        
#         updated_entity = await self._model_to_entity(fund)
        
#         # Audit logging
#         changes = {
#             'name': {'old': old_fund.name, 'new': updated_entity.name},
#             'target_amount': {'old': old_fund.target_amount, 'new': updated_entity.target_amount}
#         }
#         await AuditLogger.log_update(
#             user=None,
#             obj=fund,
#             changes=changes,
#             notes=f"Updated fund type: {updated_entity.id}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         logger.info(f"Fund type updated successfully: {updated_entity.id}")
#         return updated_entity
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cache_invalidate(
#         key_templates=[
#             "fund:{object_id}",
#             "funds:all",
#             "funds:active"
#         ],
#         namespace="funds",
#         version="1"
#     )
#     async def delete(self, object_id: int) -> bool:
#         """Soft delete a fund type with audit logging"""
#         fund = await self._get_by_id_uncached(object_id)
#         if not fund:
#             return False
        
#         # Audit logging
#         await AuditLogger.log_delete(
#             user=None,
#             obj=fund,
#             notes=f"Deleted fund type: {fund.id}",
#             ip_address="system",
#             user_agent="system"
#         )
        
#         result = await sync_to_async(super().delete)(object_id)
        
#         if result:
#             logger.info(f"Fund type deleted successfully: {fund.id}")
        
#         return result

#     # ============ QUERY OPERATIONS ============
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="funds:all:{filters}",
#         ttl=300,  # 5 minutes
#         namespace="funds",
#         version="1"
#     )
#     async def get_all(self, filters: Dict[str, Any] = None) -> List[FundTypeEntity]:
#         """Get all fund types with optional filtering"""
#         queryset = FundType.objects.filter(is_active=True)
        
#         if filters:
#             if 'is_active' in filters:
#                 queryset = queryset.filter(is_active=filters['is_active'])
        
#         funds = []
#         async for fund in queryset:
#             funds.append(await self._model_to_entity(fund))
#         return funds
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="funds:active",
#         ttl=300,  # 5 minutes
#         namespace="funds",
#         version="1"
#     )
#     async def get_active_funds(self) -> List[FundTypeEntity]:
#         """Get all active fund types"""
#         funds = []
#         async for fund in FundType.objects.filter(is_active=True):
#             funds.append(await self._model_to_entity(fund))
#         return funds
    
#     @with_db_error_handling
#     @with_retry(max_retries=3)
#     @cached(
#         key_template="fund:exists:{object_id}",
#         ttl=3600,  # 1 hour
#         namespace="funds",
#         version="1"
#     )
#     async def exists(self, object_id: int) -> bool:
#         """Check if fund type exists"""
#         return await sync_to_async(lambda: FundType.objects.filter(
#             id=object_id, is_active=True
#         ).exists())()

#     # ============ INTERNAL METHODS ============
    
#     async def _get_by_id_uncached(self, object_id: int) -> Optional[FundTypeEntity]:
#         """Internal method to get fund type by ID without cache"""
#         fund = await sync_to_async(super().get_by_id)(object_id)
#         if not fund:
#             return None
#         return await self._model_to_entity(fund)
    
#     # ============ CONVERSION METHODS ============
    
#     async def _model_to_entity(self, fund_model: FundType) -> FundTypeEntity:
#         """Convert Django model to FundTypeEntity"""
#         return FundTypeEntity(
#             id=fund_model.id,
#             name=fund_model.name,
#             description=fund_model.description,
#             target_amount=fund_model.target_amount,
#             current_amount=fund_model.current_amount,
#             is_active=fund_model.is_active,
#             created_at=fund_model.created_at,
#             updated_at=fund_model.updated_at
#         )