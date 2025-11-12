from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned
from typing import List, Any, Dict, Optional

from domain.django_exceptions import (
    ObjectNotFoundException, ObjectValidationException,
    BulkOperationException
)
from helpers.exceptions.domain.domain_exceptions import MemberNotFoundException
from .db_handler import db_error_handler
from .decorators import with_retry


class SafeManager(models.Manager):
    """
    Django model manager with comprehensive error handling
    """
    
    @db_error_handler.handle_operation
    def safe_get(self, **kwargs):
        """Get single object with proper exception handling"""
        try:
            return self.get(**kwargs)
        except ObjectDoesNotExist as e:
            raise ObjectNotFoundException(
                model=self.model.__name__,
                lookup_params=kwargs,
                cause=e
            )
        except MultipleObjectsReturned as e:
            raise ObjectValidationException(
                model=self.model.__name__,
                validation_errors={
                    'multiple_objects': f"Multiple objects found with parameters: {kwargs}"
                },
                cause=e
            )
    
    @db_error_handler.handle_operation
    def safe_get_or_none(self, **kwargs):
        """Get single object or return None if not found"""
        try:
            return self.get(**kwargs)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return None
    
    @db_error_handler.handle_operation
    def safe_create(self, **kwargs):
        """Create object with validation and error handling"""
        try:
            return self.create(**kwargs)
        except ValidationError as e:
            raise ObjectValidationException(
                model=self.model.__name__,
                validation_errors=e.message_dict,
                cause=e
            )
    
    @db_error_handler.handle_operation
    def safe_bulk_create(self, objects, batch_size=1000):
        """Bulk create with error handling"""
        try:
            return self.bulk_create(objects, batch_size=batch_size)
        except Exception as e:
            # Handle partial failures
            successful = 0
            failed_objects = []
            
            for obj in objects:
                try:
                    obj.save()
                    successful += 1
                except Exception as individual_error:
                    failed_objects.append({
                        'object': str(obj),
                        'error': str(individual_error)
                    })
            
            if failed_objects:
                raise BulkOperationException(
                    model=self.model.__name__,
                    successful=successful,
                    failed=len(failed_objects),
                    errors=failed_objects
                )
            raise
    
    @with_retry(max_retries=3)
    def atomic_update(self, **kwargs):
        """Perform atomic update with proper locking"""
        from django.db import transaction
        
        with transaction.atomic():
            obj = self.select_for_update().get(pk=kwargs.pop('pk'))
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
            return obj
    
    @db_error_handler.handle_operation
    def safe_filter(self, **kwargs):
        """Safe filter operation"""
        return self.filter(**kwargs)
    
    @db_error_handler.handle_operation
    def safe_count(self, **kwargs):
        """Safe count operation"""
        return self.filter(**kwargs).count()


# Specialized managers
class MemberManager(SafeManager):
    """Specialized manager for Member model"""
    
    @db_error_handler.handle_operation
    def find_by_email(self, email):
        try:
            return self.get(email=email)
        except ObjectDoesNotExist as e:
            raise MemberNotFoundException(lookup_params={'email': email})
    
    @db_error_handler.handle_operation
    def find_active_members(self):
        return self.filter(is_active=True).select_related('family')


class FamilyManager(SafeManager):
    """Specialized manager for Family model"""
    
    @db_error_handler.handle_operation
    def find_by_surname(self, surname):
        return self.filter(surname__iexact=surname)


class EventManager(SafeManager):
    """Specialized manager for Event model"""
    
    @db_error_handler.handle_operation
    def find_upcoming_events(self, days=30):
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)
        
        return self.filter(
            event_date__gte=start_date,
            event_date__lte=end_date
        ).order_by('event_date')