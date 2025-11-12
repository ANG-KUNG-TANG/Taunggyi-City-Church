from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
import threading
import json
from django.db import models

from apps.tcc.models.base. auditlog import AuditLog
from apps.tcc.models.base.base_model import BaseModel

User = get_user_model()

# Thread-local storage for request context
_thread_locals = threading.local()

class AuditLogMiddleware:
    """Middleware to capture request context for audit logging"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request in thread-local storage
        _thread_locals.request = request
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up
            if hasattr(_thread_locals, 'request'):
                delattr(_thread_locals, 'request')

def get_current_user():
    """Get current user from thread-local storage"""
    request = getattr(_thread_locals, 'request', None)
    if request and hasattr(request, 'user'):
        return request.user if request.user.is_authenticated else None
    return None

def get_request_info():
    """Extract request information for audit logging"""
    request = getattr(_thread_locals, 'request', None)
    if not request:
        return None, None
    
    ip_address = None
    user_agent = None
    
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT')
    
    return ip_address, user_agent

def get_field_changes(old_instance, new_instance):
    """Detect field-level changes between two instances"""
    if not old_instance or not new_instance:
        return {}
    
    changes = {}
    for field in new_instance._meta.fields:
        field_name = field.name
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(new_instance, field_name, None)
        
        # Skip certain fields
        if field_name in ['updated_at', 'version', 'meta_info']:
            continue
        
        # Convert for comparison
        if hasattr(old_value, 'pk'):
            old_value = str(old_value.pk)
        if hasattr(new_value, 'pk'):
            new_value = str(new_value.pk)
        
        if old_value != new_value:
            changes[field_name] = {
                'old': old_value,
                'new': new_value
            }
    
    return changes

def get_instance_state(instance):
    """Serialize instance state to JSON-serializable dict"""
    if not instance:
        return None
    
    state = {}
    for field in instance._meta.fields:
        field_name = field.name
        value = getattr(instance, field_name, None)
        
        # Handle different field types
        if hasattr(value, 'pk'):
            state[field_name] = str(value.pk)
        elif isinstance(value, (models.Model, models.Manager)):
            continue  # Skip model instances and managers
        else:
            state[field_name] = value
    
    return state

# Store original states for update comparison
_pre_save_states = {}

@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Capture instance state before save for update comparison"""
    # Only track models that inherit from BaseModel
    if not isinstance(instance, BaseModel):
        return
    
    # Skip if this is a create operation
    if instance.pk is None:
        return
    
    try:
        # Get the original instance from database
        original = sender.objects.get(pk=instance.pk)
        _pre_save_states[instance.pk] = {
            'instance': original,
            'state': get_instance_state(original)
        }
    except sender.DoesNotExist:
        pass

@receiver(post_save)
def log_create_update(sender, instance, created, **kwargs):
    """Log create and update operations"""
    # Only track models that inherit from BaseModel
    if not isinstance(instance, BaseModel):
        return
    
    # Skip AuditLog itself to avoid infinite recursion
    if sender == AuditLog:
        return
    
    user = get_current_user()
    ip_address, user_agent = get_request_info()
    
    action = 'CREATE' if created else 'UPDATE'
    
    # Prepare change data
    before_state = None
    after_state = get_instance_state(instance)
    changes = {}
    
    if not created:  # Update operation
        pre_save_data = _pre_save_states.pop(instance.pk, None)
        if pre_save_data:
            before_state = pre_save_data['state']
            old_instance = pre_save_data['instance']
            changes = get_field_changes(old_instance, instance)
    
    # Create audit log entry
    try:
        AuditLog.objects.create(
            content_object=instance,
            action=action,
            user=user,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes
        )
    except Exception as e:
        # Log error but don't break the application
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create audit log: {e}")

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Log delete operations"""
    # Only track models that inherit from BaseModel
    if not isinstance(instance, BaseModel):
        return
    
    # Skip AuditLog itself
    if sender == AuditLog:
        return
    
    user = get_current_user()
    ip_address, user_agent = get_request_info()
    
    # Capture state before deletion
    before_state = get_instance_state(instance)
    
    try:
        AuditLog.objects.create(
            content_object=instance,
            action='DELETE',
            user=user,
            before_state=before_state,
            after_state=None,  # No after state for delete
            ip_address=ip_address,
            user_agent=user_agent,
            changes={}
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create delete audit log: {e}")

# Custom signal for restore operations
from django.dispatch import Signal
model_restored = Signal()

@receiver(model_restored)
def log_restore(sender, instance, **kwargs):
    """Log restore operations (soft delete reversal)"""
    user = get_current_user()
    ip_address, user_agent = get_request_info()
    
    after_state = get_instance_state(instance)
    
    try:
        AuditLog.objects.create(
            content_object=instance,
            action='RESTORE',
            user=user,
            before_state=None,  # We could capture the deleted state if needed
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            changes={}
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create restore audit log: {e}")

# Utility function to manually log actions
def log_custom_action(instance, action, user=None, notes=None):
    """Manually log custom actions"""
    if not user:
        user = get_current_user()
    
    ip_address, user_agent = get_request_info()
    
    try:
        AuditLog.objects.create(
            content_object=instance,
            action=action,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            changes={'notes': notes} if notes else {}
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create custom audit log: {e}")

# Async support
@sync_to_async
def log_async_create_update(sender, instance, created, **kwargs):
    """Async wrapper for log_create_update"""
    log_create_update(sender, instance, created, **kwargs)

@sync_to_async
def log_async_delete(sender, instance, **kwargs):
    """Async wrapper for log_delete"""
    log_delete(sender, instance, **kwargs)