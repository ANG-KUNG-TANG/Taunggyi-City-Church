from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from repo.base.base_repo import ModelRepository
from apps.tcc.models.prayers.prayer import PrayerRequest, PrayerResponse
from apps.tcc.models.base.enums import PrayerPrivacy, PrayerCategory, PrayerStatus
from utils.audit_logging import AuditLogger
from models.base.permission import PermissionDenied



class PrayerRequestRepository(ModelRepository[PrayerRequest]):
    
    def __init__(self):
        super().__init__(PrayerRequest)
    
    def get_all(self, user, filters: Dict = None) -> List[PrayerRequest]:
        """
        Get prayer requests based on user permissions and privacy settings
        """
        base_queryset = PrayerRequest.objects.filter(is_active=True)
        
        if filters:
            base_queryset = base_queryset.filter(**filters)
        
        # Apply privacy filtering
        prayers = []
        for prayer in base_queryset:
            try:
                if prayer.can_view(user):
                    prayers.append(prayer)
            except PermissionDenied:
                continue
        
        return prayers
    
    def get_public_prayers(self, user, limit: int = None) -> List[PrayerRequest]:
        """Get public prayer requests"""
        queryset = PrayerRequest.objects.filter(
            is_active=True,
            privacy=PrayerPrivacy.PUBLIC,
            status=PrayerStatus.ACTIVE
        ).order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    def get_user_prayers(self, user) -> List[PrayerRequest]:
        """Get all prayer requests by a user"""
        return PrayerRequest.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at')
    
    def get_prayers_by_category(self, category: PrayerCategory, user) -> List[PrayerRequest]:
        """Get prayers by category with privacy filtering"""
        queryset = PrayerRequest.objects.filter(
            is_active=True,
            category=category,
            status=PrayerStatus.ACTIVE
        ).order_by('-created_at')
        
        prayers = []
        for prayer in queryset:
            try:
                if prayer.can_view(user):
                    prayers.append(prayer)
            except PermissionDenied:
                continue
        
        return prayers
    
    def mark_as_answered(self, prayer_id: int, user, answer_notes: str = "", request=None) -> Optional[PrayerRequest]:
        """Mark prayer request as answered"""
        prayer = self.get_by_id(prayer_id, user)
        if not prayer:
            return None
        
        # Only the prayer owner or admins can mark as answered
        if prayer.user != user and not user.can_manage_prayers:
            raise PermissionDenied("You can only mark your own prayers as answered")
        
        prayer.mark_answered(answer_notes)
        
        context, ip_address, user_agent = self._get_audit_context(request)
        AuditLogger.log_update(
            user, prayer,
            {'is_answered': {'old': False, 'new': True}},
            ip_address, user_agent,
            notes=f"Marked prayer as answered: {prayer.title}"
        )
        
        return prayer
    
    def add_prayer_response(self, prayer_id: int, user, content: str, is_private: bool = False, request=None) -> Optional[PrayerResponse]:
        """Add response to prayer request"""
        prayer = self.get_by_id(prayer_id, user)
        if not prayer:
            return None
        
        # Check if user can respond to this prayer
        if not prayer.can_view(user):
            raise PermissionDenied("You cannot respond to this prayer request")
        
        response_data = {
            'prayer_request': prayer,
            'user': user,
            'content': content,
            'is_private': is_private
        }
        
        response = PrayerResponse(**response_data)
        
        context, ip_address, user_agent = self._get_audit_context(request)
        response.save()
        
        AuditLogger.log_create(
            user, response, ip_address, user_agent,
            notes=f"Added response to prayer: {prayer.title}"
        )
        
        return response

class PrayerResponseRepository(ModelRepository[PrayerResponse]):
    
    def __init__(self):
        super().__init__(PrayerResponse)
    
    def get_responses_for_prayer(self, prayer_id: int, user) -> List[PrayerResponse]:
        """Get responses for a prayer request with privacy filtering"""
        prayer_repo = PrayerRequestRepository()
        prayer = prayer_repo.get_by_id(prayer_id, user)
        
        if not prayer:
            return []
        
        # Get all responses
        responses = PrayerResponse.objects.filter(
            prayer_request=prayer,
            is_active=True
        ).order_by('created_at')
        
        # Filter based on privacy
        visible_responses = []
        for response in responses:
            # Private responses are only visible to the prayer owner
            if response.is_private and response.prayer_request.user != user:
                continue
            visible_responses.append(response)
        
        return visible_responses