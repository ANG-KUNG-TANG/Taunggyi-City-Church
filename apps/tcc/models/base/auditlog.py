import inspect
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.tcc.models.base.base import BaseModel

# Enhanced AuditLog model
class AuditLog(BaseModel):
    """
    Comprehensive audit logging for all user actions
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PERMISSION_DENIED', 'Permission Denied'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.BigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Before and after state for updates
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    
    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    changes = models.JSONField(default=dict, help_text="Field-level changes")
    resource_type = models.CharField(max_length=100, blank=True)
    
    # Request context
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['resource_type', 'action']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} {self.resource_type} {self.object_id} by {self.user}"
    
    @property
    def is_sensitive_action(self):
        """Check if this action involves sensitive data"""
        sensitive_actions = ['DELETE', 'PERMISSION_DENIED']
        sensitive_resources = ['User', 'Donation', 'PrayerRequest']
        return self.action in sensitive_actions or self.resource_type in sensitive_resources
    
    def get_action_description(self):
        """Get human-readable action description"""
        descriptions = {
            'CREATE': f"Created {self.resource_type}",
            'READ': f"Viewed {self.resource_type}",
            'UPDATE': f"Updated {self.resource_type}",
            'DELETE': f"Deleted {self.resource_type}",
            'LOGIN': "Logged in",
            'LOGOUT': "Logged out",
            'PERMISSION_DENIED': f"Permission denied for {self.resource_type}",
        }
        return descriptions.get(self.action, f"{self.action} on {self.resource_type}")