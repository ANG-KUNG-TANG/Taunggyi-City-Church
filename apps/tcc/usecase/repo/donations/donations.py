
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal
from repo.base.base_repo import ModelRepository
from apps.tcc.models.donations.donation import Donation, FundType
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from models.base.permission import PermissionDenied
from utils.audit_logging import AuditLogger
from django.db import models


class DonationRepository(ModelRepository[Donation]):
    
    def __init__(self):
        super().__init__(Donation)
    
    def get_all(self, user, filters: Dict = None) -> List[Donation]:
        """
        Get donations - users can only see their own, admins can see all
        """
        if not user.can_manage_donations:
            # Regular users only see their own donations
            queryset = Donation.objects.filter(donor=user, is_active=True)
        else:
            queryset = Donation.objects.filter(is_active=True)
        
        if filters:
            queryset = queryset.filter(**filters)
        
        return list(queryset.order_by('-donation_date'))
    
    def get_by_id(self, id: int, user) -> Optional[Donation]:
        """
        Get donation by ID - users can only see their own
        """
        try:
            donation = Donation.objects.get(id=id, is_active=True)
            
            # Permission check
            if donation.donor != user and not user.can_manage_donations:
                raise PermissionDenied("You can only view your own donations")
            
            return donation
        except Donation.DoesNotExist:
            return None
    
    def get_user_donations(self, user) -> List[Donation]:
        """Get all donations by a user"""
        return Donation.objects.filter(
            donor=user,
            is_active=True
        ).order_by('-donation_date')
    
    def get_donations_by_fund(self, fund_id: int, user) -> List[Donation]:
        """Get donations by fund - admin only"""
        if not user.can_manage_donations:
            raise PermissionDenied("Only administrators can view donations by fund")
        
        return Donation.objects.filter(
            fund_id=fund_id,
            is_active=True
        ).order_by('-donation_date')
    
    def get_donation_summary(self, user, start_date=None, end_date=None) -> Dict[str, Any]:
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
        
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        donation_count = queryset.count()
        
        # Group by fund
        by_fund = queryset.values('fund__name').annotate(
            total=Sum('amount'),
            count=models.Count('id')
        ).order_by('-total')
        
        # Group by payment method
        by_method = queryset.values('payment_method').annotate(
            total=Sum('amount'),
            count=models.Count('id')
        ).order_by('-total')
        
        return {
            'total_amount': total_amount,
            'donation_count': donation_count,
            'by_fund': list(by_fund),
            'by_payment_method': list(by_method),
        }
    
    def process_donation(self, donation_id: int, user, request=None) -> Optional[Donation]:
        """Process donation payment - admin only"""
        if not user.can_manage_donations:
            raise PermissionDenied("Only administrators can process donations")
        
        donation = self.get_by_id(donation_id, user)
        if not donation:
            return None
        
        success = donation.process_payment()
        
        context, ip_address, user_agent = self._get_audit_context(request)
        AuditLogger.log_update(
            user, donation,
            {'status': {'old': DonationStatus.PENDING, 'new': DonationStatus.COMPLETED}},
            ip_address, user_agent,
            notes=f"Processed donation: ${donation.amount}"
        )
        
        return donation if success else None

class FundTypeRepository(ModelRepository[FundType]):
    
    def __init__(self):
        super().__init__(FundType)
    
    def get_active_funds(self, user) -> List[FundType]:
        """Get all active funds"""
        return FundType.objects.filter(is_active=True).order_by('name')
    
    def get_fund_with_stats(self, fund_id: int, user) -> Optional[Dict]:
        """Get fund with donation statistics"""
        fund = self.get_by_id(fund_id, user)
        if not fund:
            return None
        
        donations = Donation.objects.filter(
            fund=fund,
            status=DonationStatus.COMPLETED,
            is_active=True
        )
        
        total_raised = donations.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        donation_count = donations.count()
        
        recent_donations = donations.order_by('-donation_date')[:5]
        
        return {
            'fund': fund,
            'total_raised': total_raised,
            'donation_count': donation_count,
            'progress_percentage': fund.progress_percentage,
            'recent_donations': list(recent_donations),
        }