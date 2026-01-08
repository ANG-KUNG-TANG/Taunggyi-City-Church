import asyncio
import logging
from typing import Dict, Any, Optional

from asgiref.sync import sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.tcc.models.base.auditlog import AuditLog, SecurityEvent

logger = logging.getLogger(__name__)


class AsyncAuthDomainService:
    """
    Pure Domain Service - Infrastructure operations only
    No business logic, only technical implementations
    """

    @sync_to_async
    def revoke_token_async(self, token: str, user_id: Optional[int] = None) -> bool:
        """
        Infrastructure: Token revocation (blacklisting)
        """
        try:
            refresh_token = RefreshToken(token)
            user_id_from_token = refresh_token.get('user_id', user_id)
            refresh_token.blacklist()
            
            # Infrastructure: Security event logging
            self._create_security_event_async(
                user_id=user_id_from_token,
                event_type='TOKEN_REVOKED',
                description='Refresh token revoked during logout'
            )
            return True
        except Exception as e:
            # Infrastructure: Error logging
            self._create_security_event_async(
                user_id=user_id,
                event_type='TOKEN_REVOCATION_FAILED',
                description=f'Token revocation failed: {str(e)}',
                severity='HIGH'
            )
            logger.error(f"Token revocation failed: {str(e)}")
            return False
    
    # FIXED: Remove the async keyword and keep @sync_to_async
    @sync_to_async
    def audit_login_async(self, user_id: int, action: str, meta: Dict[str, Any] = None):
        """Audit login/logout events"""
        try:
            from django.contrib.auth import get_user_model
            from django.contrib.contenttypes.models import ContentType
            from apps.tcc.models.base.auditlog import AuditLog  # FIXED: Changed import path
            
            User = get_user_model()
            
            # Get the User model's content type for generic relations
            user_content_type = ContentType.objects.get_for_model(User)
            
            # Prepare changes
            ip_address = meta.get('ip') if meta else None
            user_agent = meta.get('user_agent') if meta else None
            
            changes = {
                "action": action,
                "ip_address": ip_address,
                "user_agent": user_agent[:200] if user_agent else None
            }
            
            # Create the audit log
            AuditLog.objects.create(
                user_id=user_id,
                action=action,
                content_type=user_content_type,  # Set to User content type
                object_id=user_id,               # Set to user_id
                changes=changes,
                resource_type="Auth",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            logger.info(f"Audit logged: {action} for user {user_id}")
        except Exception as e:
            logger.error(f"Audit logging failed: {e}", exc_info=True)
            # Don't raise - audit logging failure shouldn't break auth flow
            
    def _get_client_ip(self, request_meta: Dict) -> str:
        """
        Infrastructure: Extract client IP
        """
        x_forwarded_for = request_meta.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request_meta.get('REMOTE_ADDR', '')
        return ip
    
    @sync_to_async
    def _create_security_event_async(self, user_id: int, event_type: str, 
                                description: str, severity: str = 'MEDIUM') -> None:
        """
        Infrastructure: Security event logging
        """
        try:
            from apps.tcc.models import User
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass
            
            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                description=description,
                severity=severity,
            )
        except Exception as e:
            logger.error(f"Security event creation failed: {str(e)}", exc_info=True)