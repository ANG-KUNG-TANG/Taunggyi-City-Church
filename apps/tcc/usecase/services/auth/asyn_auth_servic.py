import asyncio
from asgiref.sync import sync_to_async
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.tcc.models.audit.audit import AuditLog, SecurityEvent

class AsyncAuthDomainService:
    
    @sync_to_async
    def revoke_token_async(self, token: str, user_id: int = None) -> None:
        """Async token revocation with audit logging"""
        try:
            refresh_token = RefreshToken(token)
            user_id_from_token = refresh_token.get('user_id', user_id)
            RefreshToken(token).blacklist()
            
            # Log the token revocation
            self._create_security_event_async(
                user_id=user_id_from_token,
                event_type='TOKEN_REVOKED',
                description='Refresh token revoked during logout'
            )
        except Exception as e:
            # Still log the attempt even if blacklisting fails
            self._create_security_event_async(
                user_id=user_id,
                event_type='TOKEN_REVOKED',
                description=f'Token revocation failed: {str(e)}'
            )
    
    @sync_to_async
    def audit_login_async(self, user_id: int, action: str, request_meta: dict = None) -> None:
        """Async audit logging with request context"""
        ip_address = None
        user_agent = None
        metadata = {}
        
        if request_meta:
            ip_address = self._get_client_ip(request_meta)
            user_agent = request_meta.get('HTTP_USER_AGENT', '')
            metadata = {
                'http_referer': request_meta.get('HTTP_REFERER', ''),
                'server_name': request_meta.get('SERVER_NAME', ''),
            }
        
        AuditLog.objects.create(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
    
    def _get_client_ip(self, request_meta: dict) -> str:
        """Extract client IP from request metadata"""
        x_forwarded_for = request_meta.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request_meta.get('REMOTE_ADDR')
        return ip
    
    @sync_to_async
    def _create_security_event_async(self, user_id: int, event_type: str, description: str, severity: str = 'MEDIUM'):
        """Create security event log"""
        SecurityEvent.objects.create(
            user_id=user_id,
            event_type=event_type,
            description=description,
            severity=severity
        )