from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.tcc.models.base.base import BaseModel

class AuditLogger:
    """
    Comprehensive audit logging system
    """
    
    @staticmethod
    def log_action(user, action, model_instance, resource_type="", ip_address="", user_agent="", changes=None, notes=""):
        """
        Log user actions to the audit system
        """
        from apps.tcc.models.base.auditlog import AuditLog
        
        if not user or not user.is_authenticated:
            return None
        
        # Determine resource type from model if not provided
        if not resource_type and model_instance:
            resource_type = model_instance.__class__.__name__
        
        # Get before and after state for updates
        before_state = None
        after_state = None
        
        if action == 'UPDATE' and model_instance and hasattr(model_instance, 'to_dict'):
            # This would require storing the previous state, which we can do via signals
            after_state = model_instance.to_dict(include_meta=True)
        
        audit_log = AuditLog.objects.create(
            content_object=model_instance,
            action=action,
            user=user,
            timestamp=timezone.now(),
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes or {},
            resource_type=resource_type,
            meta_info={'notes': notes}
        )
        
        return audit_log
    
    @staticmethod
    def log_user_login(user, ip_address="", user_agent=""):
        """Log user login"""
        return AuditLogger.log_action(
            user=user,
            action='LOGIN',
            model_instance=user,
            resource_type='User',
            ip_address=ip_address,
            user_agent=user_agent,
            notes='User logged in'
        )
    
    @staticmethod
    def log_user_logout(user, ip_address="", user_agent=""):
        """Log user logout"""
        return AuditLogger.log_action(
            user=user,
            action='LOGOUT',
            model_instance=user,
            resource_type='User',
            ip_address=ip_address,
            user_agent=user_agent,
            notes='User logged out'
        )
    
    @staticmethod
    def log_create(user, model_instance, ip_address="", user_agent=""):
        """Log object creation"""
        return AuditLogger.log_action(
            user=user,
            action='CREATE',
            model_instance=model_instance,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=f'Created {model_instance.__class__.__name__}'
        )
    
    @staticmethod
    def log_update(user, model_instance, changes, ip_address="", user_agent=""):
        """Log object updates"""
        return AuditLogger.log_action(
            user=user,
            action='UPDATE',
            model_instance=model_instance,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
            notes=f'Updated {model_instance.__class__.__name__}'
        )
    
    @staticmethod
    def log_delete(user, model_instance, ip_address="", user_agent=""):
        """Log object deletion"""
        return AuditLogger.log_action(
            user=user,
            action='DELETE',
            model_instance=model_instance,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=f'Deleted {model_instance.__class__.__name__}'
        )
    
    @staticmethod
    def log_view(user, model_instance, ip_address="", user_agent=""):
        """Log object viewing (for sensitive data)"""
        return AuditLogger.log_action(
            user=user,
            action='VIEW',
            model_instance=model_instance,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=f'Viewed {model_instance.__class__.__name__}'
        )
    
    @staticmethod
    def log_permission_denied(user, action, resource_type, ip_address="", user_agent=""):
        """Log permission denied attempts"""
        return AuditLogger.log_action(
            user=user,
            action='PERMISSION_DENIED',
            model_instance=None,
            resource_type=resource_type,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=f'Permission denied for {action} on {resource_type}'
        )
