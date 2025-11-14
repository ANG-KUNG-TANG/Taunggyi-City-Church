from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned
from typing import List, Any, Dict, Optional, TypeVar, Generic
from datetime import datetime

from apps.tcc.usecase.domain_exception.u_exceptions import UserNotFoundException
from core.core_exceptions.domain import (
    EntityNotFoundException, 
    ValidationException as DomainValidationException,
    BusinessRuleException
)
from .db_handler import db_error_handler
from .decorators import with_retry, atomic_operation

T = TypeVar('T', bound=models.Model)


class SafeManager(models.Manager):
    """
    Enhanced Django model manager with comprehensive error handling
    and integration with the new exception structure
    """
    
    @db_error_handler.handle_operation
    def safe_get(self, **kwargs):
        """
        Get single object with proper exception handling
        """
        try:
            return self.get(**kwargs)
        except ObjectDoesNotExist as e:
            model_name = self.model.__name__
            raise EntityNotFoundException(
                entity_name=model_name,
                entity_id=kwargs.get('id') or kwargs.get('pk'),
                details={
                    'lookup_params': kwargs,
                    'model': model_name
                }
            ) from e
        except MultipleObjectsReturned as e:
            model_name = self.model.__name__
            raise BusinessRuleException(
                rule_name="unique_object_retrieval",
                message=f"Multiple {model_name} objects found with the same criteria",
                details={
                    'model': model_name,
                    'lookup_params': kwargs
                }
            ) from e
    
    @db_error_handler.handle_operation
    def safe_get_or_none(self, **kwargs):
        """
        Get single object or return None if not found
        """
        try:
            return self.get(**kwargs)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return None
    
    @db_error_handler.handle_operation
    def safe_create(self, **kwargs):
        """
        Create object with validation and error handling
        """
        try:
            return self.create(**kwargs)
        except ValidationError as e:
            model_name = self.model.__name__
            raise DomainValidationException(
                message=f"Validation failed for {model_name}",
                field_errors=e.message_dict,
                details={
                    'model': model_name,
                    'data': kwargs
                }
            ) from e
    
    @db_error_handler.handle_operation
    def safe_bulk_create(self, objects: List[T], batch_size: int = 1000, ignore_conflicts: bool = False) -> List[T]:
        """
        Bulk create with comprehensive error handling and conflict management
        """
        if not objects:
            return []
        
        try:
            return self.bulk_create(objects, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        except Exception as e:
            # Handle partial failures gracefully
            successful_objects = []
            failed_objects = []
            
            for obj in objects:
                try:
                    obj.save()
                    successful_objects.append(obj)
                except Exception as individual_error:
                    failed_objects.append({
                        'object_repr': str(obj),
                        'error': str(individual_error),
                        'error_type': type(individual_error).__name__
                    })
            
            if failed_objects:
                model_name = self.model.__name__
                raise BusinessRuleException(
                    rule_name="bulk_operation_partial_failure",
                    message=f"Bulk create completed with {len(successful_objects)} successes and {len(failed_objects)} failures",
                    details={
                        'model': model_name,
                        'successful_count': len(successful_objects),
                        'failed_count': len(failed_objects),
                        'failed_objects': failed_objects,
                        'batch_size': batch_size
                    }
                )
            
            # If we get here, re-raise the original exception
            raise
    
    @with_retry(max_retries=3)
    def atomic_update(self, **kwargs) -> T:
        """
        Perform atomic update with proper locking and retry capability
        """
        from django.db import transaction
        
        pk = kwargs.pop('pk', None)
        if not pk:
            raise ValueError("Primary key (pk) is required for atomic update")
        
        with transaction.atomic():
            obj = self.select_for_update().get(pk=pk)
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
            return obj
    
    @db_error_handler.handle_operation
    def safe_filter(self, **kwargs):
        """
        Safe filter operation with query optimization hints
        """
        return self.filter(**kwargs)
    
    @db_error_handler.handle_operation
    def safe_count(self, **kwargs) -> int:
        """
        Safe count operation
        """
        return self.filter(**kwargs).count()
    
    @db_error_handler.handle_operation
    def safe_exists(self, **kwargs) -> bool:
        """
        Safe exists check
        """
        return self.filter(**kwargs).exists()
    
    @db_error_handler.handle_operation
    def safe_update_or_create(self, defaults: Dict[str, Any] = None, **kwargs) -> T:
        """
        Safe update or create operation
        """
        try:
            obj, created = self.update_or_create(defaults=defaults or {}, **kwargs)
            return obj
        except ValidationError as e:
            model_name = self.model.__name__
            raise DomainValidationException(
                message=f"Validation failed in update_or_create for {model_name}",
                field_errors=e.message_dict,
                details={
                    'model': model_name,
                    'lookup_params': kwargs,
                    'defaults': defaults
                }
            ) from e
    
    def get_recently_modified(self, hours: int = 24):
        """
        Get objects modified in the last specified hours
        """
        from django.utils import timezone
        cutoff_time = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(updated_at__gte=cutoff_time)


# Specialized managers for different domains
class UserManager(SafeManager):
    """
    Specialized manager for User model with domain-specific methods
    """
    
    @db_error_handler.handle_operation
    def find_by_email(self, email: str):
        """
        Find user by email with proper exception handling
        """
        try:
            return self.get(email__iexact=email)
        except ObjectDoesNotExist as e:
            raise UserNotFoundException(
                email=email,
                details={'lookup_field': 'email', 'value': email}
            ) from e
    
    @db_error_handler.handle_operation
    def find_active_users(self):
        """
        Find all active users with related data
        """
        return self.filter(is_active=True).select_related('profile')
    
    @db_error_handler.handle_operation
    def find_users_by_role(self, role: str):
        """
        Find users by role
        """
        return self.filter(role=role, is_active=True)
    
    @with_retry(max_retries=2)
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user with retry capability
        """
        from django.db import transaction
        
        with transaction.atomic():
            user = self.select_for_update().get(pk=user_id)
            user.is_active = False
            user.save()
            return True


class SermonManager(SafeManager):
    """
    Specialized manager for Sermon model
    """
    
    @db_error_handler.handle_operation
    def find_recent_sermons(self, days: int = 30):
        """
        Find sermons from the last specified days
        """
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        return self.filter(
            sermon_date__gte=start_date
        ).order_by('-sermon_date')
    
    @db_error_handler.handle_operation
    def find_by_preacher(self, preacher_name: str):
        """
        Find sermons by preacher name
        """
        return self.filter(preacher__icontains=preacher_name).order_by('-sermon_date')
    
    @db_error_handler.handle_operation
    def find_by_bible_passage(self, passage: str):
        """
        Find sermons by bible passage
        """
        return self.filter(bible_passage__icontains=passage)


class EventManager(SafeManager):
    """
    Specialized manager for Event model
    """
    
    @db_error_handler.handle_operation
    def find_upcoming_events(self, days: int = 30):
        """
        Find upcoming events within the specified days
        """
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)
        
        return self.filter(
            start_date__gte=start_date,
            start_date__lte=end_date
        ).order_by('start_date')
    
    @db_error_handler.handle_operation
    def find_ongoing_events(self):
        """
        Find events that are currently ongoing
        """
        from django.utils import timezone
        
        now = timezone.now()
        return self.filter(
            start_date__lte=now,
            end_date__gte=now
        ).order_by('start_date')


class DonationManager(SafeManager):
    """
    Specialized manager for Donation model
    """
    
    @db_error_handler.handle_operation
    def find_recent_donations(self, days: int = 30):
        """
        Find donations from the last specified days
        """
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        return self.filter(
            donation_date__gte=start_date
        ).order_by('-donation_date')
    
    @db_error_handler.handle_operation
    def find_by_user(self, user_id: int):
        """
        Find donations by user ID
        """
        return self.filter(user_id=user_id).order_by('-donation_date')
    
    @db_error_handler.handle_operation
    def get_donation_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get donation summary for the specified period
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Sum, Count
        
        start_date = timezone.now() - timedelta(days=days)
        
        summary = self.filter(
            donation_date__gte=start_date,
            status='completed'
        ).aggregate(
            total_amount=Sum('amount'),
            total_donations=Count('id'),
            average_amount=Sum('amount') / Count('id')
        )
        
        return summary