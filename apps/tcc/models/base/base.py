import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json

from apps.tcc.models.base.manager import BaseModelManager
from apps.tcc.utils.fields import SnowflakeField

User = get_user_model()


class BaseModel(models.Model):
    """
    Universal foundation model providing consistent metadata, security, 
    and utilities for all domain models.
    """
    
    # Core Identity & Tracking
    id = SnowflakeField(
        verbose_name="Unique Identifier"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now, 
        editable=False,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated At"
    )
    
    # User References
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        editable=False,
        verbose_name="Created By"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name="Last Updated By"
    )
    
    # Soft Delete & Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name="Deleted At"
    )
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted',
        editable=False,
        verbose_name="Deleted By"
    )
    
    # Metadata & Configuration
    meta_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Meta Information",
        help_text="Additional metadata stored as JSON"
    )
    
    # Versioning & Audit
    version = models.PositiveIntegerField(
        default=1,
        editable=False,
        verbose_name="Version"
    )
    
    # Custom Manager
    objects = BaseModelManager()
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        """Default string representation"""
        return f"{self.__class__.__name__} ({self.id})"
    
    def __repr__(self):
        """Detailed representation for debugging"""
        return f"<{self.__class__.__name__} {self.id} active={self.is_active}>"
    
    def save(self, *args, **kwargs):
        """Override save to handle timestamps, versioning, and validation"""
        
        # Pre-save validation
        self.full_clean()
        
        # Update timestamps and version
        if not self.created_at:
            self.created_at = timezone.now()
        
        # Increment version on updates
        if self.pk:
            self.version += 1
        
        # Set updated_by if provided in kwargs
        user = kwargs.pop('user', None)
        if user and user.is_authenticated:
            if not self.pk:  # Creating
                self.created_by = user
            self.updated_by = user
        
        super().save(*args, **kwargs)
    
    def soft_delete(self, user=None):
        """
        Soft delete the record by marking as inactive
        """
        if not self.is_active:
            return  # Already deleted
        
        self.is_active = False
        self.deleted_at = timezone.now()
        
        if user and user.is_authenticated:
            self.deleted_by = user
        
        # Save without triggering signals if needed
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])
    
    def restore(self, user=None):
        """
        Restore a soft-deleted record
        """
        if self.is_active:
            return  # Already active
        
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        
        if user and user.is_authenticated:
            self.updated_by = user
        
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by', 'updated_by'])
        from apps.tcc.models.base.signals import model_restored
        model_restored.send(sender=self.__class__, instance=self)
        
    def hard_delete(self, *args, **kwargs):
        """
        Permanent deletion - use with caution
        """
        super().delete(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        Override delete to use soft delete by default
        """
        user = kwargs.pop('user', None)
        self.soft_delete(user=user)
    
    # Permission & Security Methods
    def can_view(self, user):
        """
        Check if user can view this object
        Override in subclasses for custom logic
        """
        if not user or not user.is_authenticated:
            return False
        
        # Admin can view everything
        if hasattr(user, 'is_admin') and user.is_admin:
            return True
        
        # Created by user
        if self.created_by == user:
            return True
        
        # Zone leader logic can be added in subclasses
        return False
    
    def can_edit(self, user):
        """
        Check if user can edit this object
        """
        if not user or not user.is_authenticated:
            return False
        
        # Admin can edit everything
        if hasattr(user, 'is_admin') and user.is_admin:
            return True
        
        # Created by user (and not deleted)
        if self.created_by == user and self.is_active:
            return True
        
        # Zone leader logic can be added in subclasses
        return False
    
    def can_delete(self, user):
        """
        Check if user can delete this object
        """
        if not user or not user.is_authenticated:
            return False
        
        # Admin can delete everything
        if hasattr(user, 'is_admin') and user.is_admin:
            return True
        
        # Created by user (and not already deleted)
        if self.created_by == user and self.is_active:
            return True
        
        return False
    
    # Utility Methods
    def get_meta_value(self, key, default=None):
        """Safely get value from meta_info"""
        return self.meta_info.get(key, default)
    
    def set_meta_value(self, key, value):
        """Safely set value in meta_info"""
        if not self.meta_info:
            self.meta_info = {}
        self.meta_info[key] = value
        self.save(update_fields=['meta_info'])
    
    def update_meta(self, **kwargs):
        """Update multiple meta values at once"""
        if not self.meta_info:
            self.meta_info = {}
        self.meta_info.update(kwargs)
        self.save(update_fields=['meta_info'])
    
    def to_dict(self, include_meta=False):
        """
        Convert model to dictionary representation
        """
        data = {
            'id': str(self.id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'version': self.version,
        }
        
        if include_meta:
            data['meta_info'] = self.meta_info
        
        return data
    
    def clone(self, user=None, **overrides):
        """
        Create a copy of this instance with new UUID
        """
        model_class = self.__class__
        
        # Prepare field values
        fields = {}
        for field in model_class._meta.fields:
            if field.name == 'id':
                continue  # Skip ID for new instance
            elif field.name in ['created_at', 'updated_at', 'created_by', 'updated_by']:
                continue  # These will be set automatically
            else:
                fields[field.name] = getattr(self, field.name)
        
        # Apply overrides
        fields.update(overrides)
        
        # Create new instance
        new_instance = model_class(**fields)
        
        # Save with user context
        if user:
            new_instance.save(user=user)
        else:
            new_instance.save()
        
        return new_instance
    
    
    def save_with_audit(self, user, request=None, *args, **kwargs):
        """
        Save with automatic audit logging
        """
        is_new = self._state.adding
        action = 'CREATE' if is_new else 'UPDATE'
        
        # Get request info if available
        ip_address = ""
        user_agent = ""
        request_path = ""
        request_method = ""
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            request_path = request.path
            request_method = request.method
        
        # Save the object
        self.save(*args, **kwargs)
        
        # Log the action
        from apps.tcc.utils.audit_logging import AuditLogger
        
        if is_new:
            AuditLogger.log_create(user, self, ip_address, user_agent)
        else:
            # For updates, you might want to track what changed
            changes = self._get_changes()
            AuditLogger.log_update(user, self, changes, ip_address, user_agent)
    
    def delete_with_audit(self, user, request=None, *args, **kwargs):
        """
        Delete with automatic audit logging
        """
        # Get request info if available
        ip_address = ""
        user_agent = ""
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log before deletion
        from apps.tcc.utils.audit_logging import AuditLogger
        AuditLogger.log_delete(user, self, ip_address, user_agent)
        
        # Perform deletion (soft delete by default)
        self.soft_delete(user=user)
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_changes(self):
        """Get changes made in this update (simplified version)"""
        # This would need to be implemented based on your specific needs
        # You might want to use django-model-utils or similar for change tracking
        return {}