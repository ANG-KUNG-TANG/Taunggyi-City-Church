from django.db import models
from django.utils import timezone
from django.conf import settings  # Add this
from apps.tcc.utils.snowflake import generate_snowflake_id, decompose_snowflake_id


class BaseModelManager(models.Manager):
    """Custom manager for BaseModel with Snowflake ID support"""
    
    def get_queryset(self):
        """Return only active objects by default"""
        return super().get_queryset().filter(is_active=True)
    
    def all_with_inactive(self):
        """Return all objects including inactive ones"""
        return super().get_queryset()
    
    def inactive(self):
        """Return only inactive objects"""
        return super().get_queryset().filter(is_active=False)
    
    def create_with_id(self, **kwargs):
        """Create object with explicit Snowflake ID"""
        if 'id' not in kwargs:
            kwargs['id'] = generate_snowflake_id()
        return self.create(**kwargs)
    
    def bulk_create_with_ids(self, objs, batch_size=None):
        """Bulk create objects with Snowflake IDs"""
        for obj in objs:
            if not obj.id:
                obj.id = generate_snowflake_id()
        return super().bulk_create(objs, batch_size=batch_size)
    
    def get_by_snowflake(self, snowflake_id):
        """Get object by Snowflake ID"""
        return self.get_queryset().get(id=snowflake_id)
    
    def filter_by_snowflake_range(self, start_id, end_id):
        """Filter objects by Snowflake ID range"""
        return self.get_queryset().filter(id__range=(start_id, end_id))


class BaseModel(models.Model):
    """Base model with Snowflake ID instead of UUID"""
    
    # Use Snowflake ID as primary key
    id = models.BigIntegerField(
        primary_key=True,
        default=generate_snowflake_id,
        editable=False,
        verbose_name="ID"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User References - Use settings.AUTH_USER_MODEL with a lambda to avoid circular imports
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )
    
    # Basic fields
    is_active = models.BooleanField(default=True)
    
    # Meta information
    meta_info = models.JSONField(default=dict, blank=True)
    
    # Version for optimistic locking
    version = models.PositiveIntegerField(default=1, editable=False)
    
    # Soft delete fields
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted'
    )
    
    # Custom manager
    objects = BaseModelManager()
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.__class__.__name__} ({self.id})"

    def __repr__(self):
        """Detailed representation for debugging"""
        return f"<{self.__class__.__name__} {self.id} active={self.is_active}>"
    
    def get_snowflake_info(self):
        """
        Decompose the Snowflake ID to get timestamp, datacenter, machine, and sequence info
        """
        return decompose_snowflake_id(self.id)
    
    def get_created_timestamp(self):
        """
        Get the actual creation timestamp from Snowflake ID
        Useful for auditing when created_at might be different
        """
        snowflake_info = self.get_snowflake_info()
        return snowflake_info.get('datetime') if snowflake_info else None
    
    @classmethod
    def generate_id(cls):
        """Generate a new Snowflake ID"""
        return generate_snowflake_id()
    
    def save(self, *args, **kwargs):
        """Override save to handle Snowflake ID generation and validation"""
        
        is_new = self._state.adding
        # Generate Snowflake ID if this is a new instance
        if not self.id:
            self.id = generate_snowflake_id()
        
        # Update timestamps
        if not self.created_at:
            self.created_at = timezone.now()
        
        # Increment version on updates
        if not is_new:
            self.version += 1
        
        # Set updated_by if provided in kwargs
        user = kwargs.pop('user', None)
        if user:
            # User is passed as an instance, not as a model class
            if is_new and not self.created_by:
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
        
        if user:
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
        
        if user:
            self.updated_by = user
        
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by', 'updated_by'])
    
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
    
    # Permission & Security Methods - Simplified to avoid circular imports
    def can_view(self, user):
        """
        Check if user can view this object
        """
        if not user:
            return False
        
        # Admin can view everything
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        
        # Created by user
        if self.created_by and self.created_by.id == user.id:
            return True
        
        return False
    
    def can_edit(self, user):
        """
        Check if user can edit this object
        """
        if not user:
            return False
        
        # Admin can edit everything
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        
        # Created by user (and not deleted)
        if self.created_by and self.created_by.id == user.id and self.is_active:
            return True
        
        return False
    
    def can_delete(self, user):
        """
        Check if user can delete this object
        """
        if not user:
            return False
        
        # Admin can delete everything
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        
        # Created by user (and not already deleted)
        if self.created_by and self.created_by.id == user.id and self.is_active:
            return True
        
        return False
    
    # Utility Methods
    def get_meta_value(self, key, default=None):
        """Safely get value from meta_info"""
        return self.meta_info.get(key, default) if self.meta_info else default
    
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
    
    def to_dict(self, include_meta=False, include_snowflake_info=False):
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
        
        if include_snowflake_info:
            data['snowflake_info'] = self.get_snowflake_info()
        
        return data
    
    def clone(self, user=None, **overrides):
        """
        Create a copy of this instance with new Snowflake ID
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
        
        # Create new instance (will auto-generate Snowflake ID)
        new_instance = model_class(**fields)
        
        # Save with user context
        if user:
            new_instance.save(user=user)
        else:
            new_instance.save()
        
        return new_instance
    
    @classmethod
    def get_by_snowflake_id(cls, snowflake_id):
        """
        Get object by Snowflake ID with caching support
        """
        try:
            return cls.objects.get(id=snowflake_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_snowflake_ids(cls, snowflake_ids):
        """
        Get multiple objects by Snowflake IDs
        """
        return cls.objects.filter(id__in=snowflake_ids)
    
    def get_creation_time_from_id(self):
        """
        Extract creation time from Snowflake ID
        Useful when you need the exact time the ID was generated
        """
        info = self.get_snowflake_info()
        return info.get('datetime') if info else None