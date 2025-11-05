from django.db import models
from django.core.exceptions import ValidationError

class BaseModelManager(models.Manager):
    """Custom manager for BaseModel that handles soft deletion"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def all_with_inactive(self):
        """Return all objects including inactive ones"""
        return super().get_queryset()
    
    def inactive(self):
        """Return only inactive objects"""
        return super().get_queryset().filter(is_active=False)
    
    def get_or_none(self, **kwargs):
        """Safe get that returns None instead of raising exception"""
        try:
            return self.get(**kwargs)
        except (self.model.DoesNotExist, ValidationError):
            return None