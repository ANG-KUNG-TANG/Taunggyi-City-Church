from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('REFRESH_TOKEN', 'Token Refresh'),
        ('VERIFY_TOKEN', 'Token Verify'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PROFILE_UPDATE', 'Profile Update'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True,  # Allow null for system events
        blank=True
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional context
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'System'} - {self.action} - {self.timestamp}"

class SecurityEvent(models.Model):
    EVENT_CHOICES = [
        ('INVALID_CREDENTIALS', 'Invalid Credentials'),
        ('ACCOUNT_LOCKOUT', 'Account Lockout'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('TOKEN_REVOKED', 'Token Revoked'),
        ('PASSWORD_RESET_REQUEST', 'Password Reset Request'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    severity = models.CharField(
        max_length=10,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],
        default='MEDIUM'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} - {self.user.email if self.user else 'Unknown'} - {self.timestamp}"