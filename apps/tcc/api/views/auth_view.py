from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.base.jwt_uc import JWTCreateUseCase

from .base_view import BaseView


class LoginView(BaseView, APIView):
    """User login endpoint with enhanced audit logging"""
    permission_classes = [AllowAny]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),  # Integrated service
            jwt_provider=JWTCreateUseCase()
        )
        
        result = await controller.login(request.data, self.build_context(request))
        return self.create_response(result, "POST")


class LogoutView(BaseView, APIView):
    """User logout endpoint with token revocation"""
    permission_classes = [IsAuthenticated]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),  # Integrated service
            jwt_provider=JWTCreateUseCase()
        )
        
        result = await controller.logout(request.data, request.user, self.build_context(request))
        return self.create_response(result, "POST")


class RefreshTokenView(BaseView, APIView):
    """Token refresh endpoint"""
    permission_classes = [AllowAny]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),  # Integrated service
            jwt_provider=JWTCreateUseCase()
        )
        
        result = await controller.refresh_token(request.data, self.build_context(request))
        return self.create_response(result, "POST")


class VerifyTokenView(BaseView, APIView):
    """Token verification endpoint"""
    permission_classes = [IsAuthenticated]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),  # Integrated service
            jwt_provider=JWTCreateUseCase()
        )
        
        result = await controller.verify_token(request.user, self.build_context(request))
        return self.create_response(result, "POST")


# NEW: Admin endpoints using direct service operations
class AdminTokenRevocationView(BaseView, APIView):
    """Admin endpoint for forced token revocation"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),
            jwt_provider=JWTCreateUseCase()
        )
        
        token = request.data.get('token')
        user_id = request.data.get('user_id')
        
        if not token:
            return Response({
                "success": False,
                "message": "Token is required",
                "error_code": "MISSING_TOKEN"
            }, status=400)
        
        result = await controller.revoke_token_direct(token, user_id, self.build_context(request))
        return self.create_response(result, "POST")


class SecurityEventView(BaseView, APIView):
    """Endpoint for logging custom security events"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def post(self, request: Request) -> Response:
        controller = create_auth_controller(
            user_repository=UserRepository(),
            auth_service=AsyncAuthDomainService(),
            jwt_provider=JWTCreateUseCase()
        )
        
        result = await controller.audit_security_event(
            user_id=request.data.get('user_id', request.user.id),
            event_type=request.data.get('event_type'),
            description=request.data.get('description'),
            severity=request.data.get('severity', 'MEDIUM'),
            context=self.build_context(request)
        )
        
        return self.create_response(result, "POST")


class AuditLogsView(BaseView, APIView):
    """Endpoint to view audit logs (read-only)"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def get(self, request: Request) -> Response:
        # This would typically call a use case to retrieve audit logs
        # Simplified for example purposes
        from apps.tcc.models.audit.audit import AuditLog
        from django.utils import timezone
        from datetime import timedelta
        
        # Get recent logs (last 7 days)
        since = timezone.now() - timedelta(days=7)
        
        # This would need to be async in production
        logs = AuditLog.objects.filter(
            timestamp__gte=since
        ).order_by('-timestamp')[:100]  # Limit to 100 most recent
        
        log_data = []
        for log in logs:
            log_data.append({
                'id': log.id,
                'user_id': log.user_id,
                'action': log.action,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
                'user_agent': log.user_agent
            })
        
        return Response({
            "success": True,
            "message": "Audit logs retrieved successfully",
            "data": {
                "logs": log_data,
                "total_count": len(log_data)
            }
        })


# Protected example endpoints
class ProtectedView(BaseView, APIView):
    """Example protected endpoint"""
    permission_classes = [IsAuthenticated]

    async def get(self, request: Request) -> Response:
        return Response({
            "success": True,
            "message": "Access granted to protected resource",
            "data": {
                "user_id": str(request.user.id),
                "email": request.user.email,
                "role": getattr(request.user, 'role', 'user')
            }
        })