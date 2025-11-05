from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
# Mixins for Additional Functionality


User = get_user_model()

class StatusMixin(models.Model):
    """
    Mixin for models that need status workflow
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name="Status"
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_status_changes'
    )
    
    class Meta:
        abstract = True
    
    def set_status(self, new_status, user=None):
        """Change status with audit"""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_changed_by = user
        self.save()
        
        # Log status change
        return old_status, new_status

