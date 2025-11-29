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
    
    @sync_to_async
    def audit_login_async(self, user_id: int, action: str, request_meta: Optional[Dict] = None) -> None:
        """
        Infrastructure: Audit logging
        """
        try:
            ip_address = None
            user_agent = None
            metadata = {}
            
            if request_meta:
                ip_address = self._get_client_ip(request_meta)
                user_agent = request_meta.get('HTTP_USER_AGENT', '')[:500]
                metadata = {
                    'http_referer': request_meta.get('HTTP_REFERER', ''),
                    'server_name': request_meta.get('SERVER_NAME', ''),
                }
            
            # Infrastructure: Database operation
            AuditLog.objects.create(
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Audit logging failed: {str(e)}")
            # Infrastructure: Error handling
            self._create_security_event_async(
                user_id=user_id,
                event_type='AUDIT_LOG_FAILED',
                description=f'Audit logging failed: {str(e)}',
                severity='MEDIUM'
            )

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
            SecurityEvent.objects.create(
                user_id=user_id,
                event_type=event_type,
                description=description,
                severity=severity,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Security event creation failed: {str(e)}")
