from datetime import timezone
from apps.tcc.models.base.base_model import BaseModel
from apps.tcc.models.base.enums import PrayerCategory, PrayerPrivacy, PrayerStatus, UserRole
from django.db import models
from apps.tcc.models.users.users import User


class Prayer(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prayer_requests'
    )
    title = models.CharField(
        max_length=200,
        help_text="Brief title for the prayer request"
    )
    content = models.TextField(help_text="Prayer request details")
    
    privacy = models.CharField(
        max_length=20,
        choices=PrayerPrivacy.choices,
        default=PrayerPrivacy.CONGREGATION,
        help_text="Who can see this prayer request"
    )
    category = models.CharField(
        max_length=20,
        choices=PrayerCategory.choices,
        default=PrayerCategory.OTHER
    )
    status = models.CharField(
        max_length=20,
        choices=PrayerStatus.choices,
        default=PrayerStatus.ACTIVE
    )
    
    is_answered = models.BooleanField(default=False)
    answered_at = models.DateTimeField(null=True, blank=True)
    answer_notes = models.TextField(
        blank=True,
        help_text="Notes about how the prayer was answered"
    )
    
    # Optional expiration for prayer requests
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this prayer request expires"
    )
    
    class Meta:
        db_table = "prayer_requests"
        verbose_name = "Prayer Request"
        verbose_name_plural = "Prayer Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['privacy', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['category', 'is_answered']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.name}"
    
    def can_view(self, user):
        """Override base can_view for prayer request visibility"""
        if not user or not user.is_authenticated:
            return False
        
        # User can view their own requests
        if self.user == user:
            return True
        
        # Public requests can be viewed by anyone
        if self.privacy == PrayerPrivacy.PUBLIC:
            return True
        
        # Congregation requests can be viewed by members
        if self.privacy == PrayerPrivacy.CONGREGATION and user.is_member:
            return True
        
        # Leaders can view all requests
        if self.privacy == PrayerPrivacy.LEADERS_ONLY and user.is_leader:
            return True
        
        # Staff and super admins can view everything
        if user.role in [UserRole.STAFF, UserRole.SUPER_ADMIN]:
            return True
        
        return False
    
    def mark_answered(self, notes=""):
        """Mark prayer as answered"""
        self.is_answered = True
        self.status = PrayerStatus.ANSWERED
        self.answered_at = timezone.now()
        self.answer_notes = notes
        self.save()
    
    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class PrayerResponse(BaseModel):
    prayer_request = models.ForeignKey(
        Prayer,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='prayer_responses'
    )
    content = models.TextField(help_text="Prayer response or support message")
    is_private = models.BooleanField(
        default=False,
        help_text="Whether this response is private to the prayer request owner"
    )
    
    class Meta:
        db_table = "prayer_responses"
        verbose_name = "Prayer Response"
        verbose_name_plural = "Prayer Responses"
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response by {self.user.name} to {self.prayer_request.title}"