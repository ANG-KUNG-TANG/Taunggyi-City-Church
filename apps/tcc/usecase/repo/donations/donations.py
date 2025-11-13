from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal
from repo.base.modelrepo import ModelRepository
from apps.tcc.models.donations.donation import Donation, FundType
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from models.base.permission import PermissionDenied
from utils.audit_logging import AuditLogger
from django.db import models
from core.db.decorators import with_db_error_handling, with_retry


class DonationRepository(ModelRepository[Donation]):
    
    def __init__(self):
        super().__init__(Donation)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_all(self, user, filters: Dict = None) -> List[Donation]:
        """
        Get donations - users can only see their own, admins can see all
        """
        if not user.can_manage_donations:
            # Regular users only see their own donations
            queryset = Donation.objects.filter(donor=user, is_active=True)
        else:
            queryset = Donation.objects.filter(is_active=True)
        
        if filters:
            for key, value in filters.items():
                queryset = queryset.filter(**{key: value})
        
        donations = []
        async for donation in queryset.order_by('-donation_date'):
            donations.append(donation)
        return donations
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_by_id(self, id: int, user) -> Optional[Donation]:
        """
        Get donation by ID - users can only see their own
        """
        try:
            donation = await Donation.objects.aget(id=id, is_active=True)
            
            # Permission check
            if donation.donor != user and not user.can_manage_donations:
                raise PermissionDenied("You can only view your own donations")
            
            return donation
        except Donation.DoesNotExist:
            return None
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_user_donations(self, user) -> List[Donation]:
        """Get all donations by a user"""
        donations = []
        async for donation in Donation.objects.filter(
            donor=user,
            is_active=True
        ).order_by('-donation_date'):
            donations.append(donation)
        return donations
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_donations_by_fund(self, fund_id: int, user) -> List[Donation]:
        """Get donations by fund - admin only"""
        if not user.can_manage_donations:
            raise PermissionDenied("Only administrators can view donations by fund")
        
        donations = []
        async for donation in Donation.objects.filter(
            fund_id=fund_id,
            is_active=True
        ).order_by('-donation_date'):
            donations.append(donation)
        return donations
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_donation_summary(self, user, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get donation summary - admin only"""
        if not user.can_manage_donations:
            raise PermissionDenied("Only administrators can view donation summaries")
        
        queryset = Donation.objects.filter(
            is_active=True,
            status=DonationStatus.COMPLETED
        )
        
        if start_date:
            queryset = queryset.filter(donation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(donation_date__lte=end_date)
        
        total_amount = await queryset.aaggregate(total=Sum('amount'))
        total_amount = total_amount['total'] or Decimal('0')
        
        donation_count = await queryset.acount()
        
        # Group by fund
        by_fund = []
        async for item in queryset.values('fund__name').annotate(
            total=Sum('amount'),
            count=models.Count('id')
        ).order_by('-total'):
            by_fund.append(item)
        
        # Group by payment method
        by_method = []
        async for item in queryset.values('payment_method').annotate(
            total=Sum('amount'),
            count=models.Count('id')
        ).order_by('-total'):
            by_method.append(item)
        
        return {
            'total_amount': total_amount,
            'donation_count': donation_count,
            'by_fund': by_fund,
            'by_payment_method': by_method,
        }
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def process_donation(self, donation_id: int, user, request=None) -> Optional[Donation]:
        """Process donation payment - admin only"""
        if not user.can_manage_donations:
            raise PermissionDenied("Only administrators can process donations")
        
        donation = await self.get_by_id(donation_id, user)
        if not donation:
            return None
        
        success = await donation.process_payment()
        
        context, ip_address, user_agent = await self._get_audit_context(request)
        await AuditLogger.log_update(
            user, donation,
            {'status': {'old': DonationStatus.PENDING, 'new': DonationStatus.COMPLETED}},
            ip_address, user_agent,
            notes=f"Processed donation: ${donation.amount}"
        )
        
        return donation if success else None


class FundTypeRepository(ModelRepository[FundType]):
    
    def __init__(self):
        super().__init__(FundType)
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_active_funds(self, user) -> List[FundType]:
        """Get all active funds"""
        funds = []
        async for fund in FundType.objects.filter(is_active=True).order_by('name'):
            funds.append(fund)
        return funds
    
    @with_db_error_handling
    @with_retry(max_retries=3)
    async def get_fund_with_stats(self, fund_id: int, user) -> Optional[Dict]:
        """Get fund with donation statistics"""
        fund = await self.get_by_id(fund_id, user)
        if not fund:
            return None
        
        donations = Donation.objects.filter(
            fund=fund,
            status=DonationStatus.COMPLETED,
            is_active=True
        )
        
        total_raised = await donations.aaggregate(total=Sum('amount'))
        total_raised = total_raised['total'] or Decimal('0')
        
        donation_count = await donations.acount()
        
        recent_donations = []
        async for donation in donations.order_by('-donation_date')[:5]:
            recent_donations.append(donation)
        
        return {
            'fund': fund,
            'total_raised': total_raised,
            'donation_count': donation_count,
            'progress_percentage': fund.progress_percentage,
            'recent_donations': recent_donations,
        }