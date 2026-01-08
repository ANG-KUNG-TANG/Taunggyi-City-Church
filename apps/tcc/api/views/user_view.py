import logging
import inspect
from datetime import datetime
import re
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.views import APIView
from asgiref.sync import async_to_sync

from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema,
    UserUpdateInputSchema,
    UserQueryInputSchema,
    EmailCheckInputSchema,
)
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.users.user_controller import get_user_controller
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
)
from apps.core.core_exceptions.domain import (
    DomainValidationException,
    DomainException
)
from .base_view import get_pagination_params, extract_filters, build_context

logger = logging.getLogger(__name__)


class RootView(APIView):
    """Public API root endpoint"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return API information"""
        return Response({
            "message": "TCC API Server",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/tcc/health/",
                "register": "/tcc/users/register/",
                "login": "/tcc/auth/login/",
                "profile": "/tcc/users/profile/",
                "check_email": "/tcc/users/check-email/",
                "auth": {
                    "login": "/tcc/auth/login/",
                    "logout": "/tcc/auth/logout/",
                    "refresh": "/tcc/auth/refresh/",
                    "verify": "/tcc/auth/verify/",
                    "forgot_password": "/tcc/auth/forgot-password/",
                    "reset_password": "/tcc/auth/reset-password/"
                }
            }
        })
# ============================================
# HELPER FUNCTIONS
# ============================================

def entity_to_dict(entity) -> dict:
    """Convert entity to dictionary for API response"""
    if not entity:
        return {}
    
    try:
        entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity.dict()
    except:
        entity_dict = entity.__dict__.copy() if hasattr(entity, '__dict__') else {}
    
    # Remove sensitive fields
    sensitive_fields = ['password', 'password_hash', 'salt', 'tokens', 'refresh_token', 'access_token']
    for field in sensitive_fields:
        entity_dict.pop(field, None)
    
    # Convert dates to ISO format
    date_fields = ['created_at', 'updated_at', 'last_login', 'date_of_birth']
    for field in date_fields:
        if field in entity_dict and entity_dict[field]:
            value = entity_dict[field]
            if hasattr(value, 'isoformat'):
                entity_dict[field] = value.isoformat()
    
    return entity_dict


def handle_exception(e: Exception, operation: str) -> Response:
    """Centralized exception handling with proper DRF Response"""
    logger.error(f"{operation} error: {e}", exc_info=True)
    
    error_mapping = {
        UserNotFoundException: ("USER_NOT_FOUND", 404),
        UserAlreadyExistsException: ("USER_ALREADY_EXISTS", 409),
        DomainValidationException: ("VALIDATION_ERROR", 400),
    }
    
    error_code, status_code = error_mapping.get(
        type(e), 
        ("INTERNAL_ERROR", 500)
    )
    
    return Response({
        "success": False,
        "message": str(e),
        "error_code": error_code,
        "status_code": status_code
    }, status=status_code)


def safe_get_controller():
    """
    Safely get controller instance, handling both sync and async factories
    """
    try:
        controller = get_user_controller()
        
        # If it's a coroutine, await it
        if inspect.iscoroutine(controller):
            controller = async_to_sync(lambda: controller)()
        
        return controller
    except Exception as e:
        logger.error(f"Failed to get controller: {e}", exc_info=True)
        raise


# ============================================
# BASE VIEW - Standard DRF
# ============================================

class BaseAPIView(APIView):
    """Base view with common functionality"""
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_current_user(self, request):
        """Extract authenticated user from request"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        return None
    
    def get_context(self, request):
        """Get context for controller calls"""
        return build_context(request)
    
    def get_controller(self):
        """Get user controller instance - handles both sync and async"""
        return safe_get_controller()
    
    def call_async_method(self, method, *args, **kwargs):
        """
        Helper to call async controller methods from sync views.
        Wraps async_to_sync for cleaner code.
        """
        try:
            return async_to_sync(method)(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling async method {method.__name__}: {e}", exc_info=True)
            raise


# ============================================
# PUBLIC ENDPOINTS
# ============================================

class RegisterView(BaseAPIView):
    """User registration - Public endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Register a new user"""
        try:
            user_data = UserCreateInputSchema(**request.data)
            controller = self.get_controller()
            
            user_entity = self.call_async_method(
                controller.register_user,
                user_data=user_data,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="User registered successfully",
                    status_code=status.HTTP_201_CREATED
                ).to_dict(),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return handle_exception(e, "Registration")


class EmailAvailabilityView(BaseAPIView):
    """Check email availability - Public endpoint"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Check if email is available"""
        try:
            email = request.query_params.get('email')
            if not email:
                return Response({
                    "success": False,
                    "message": "Email parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            email_data = EmailCheckInputSchema(email=email)
            controller = self.get_controller()
            
            result = self.call_async_method(
                controller.check_email_availability,
                validated_data=email_data,
                context=self.get_context(request)
            )
            
            response_data = {
                'email': email,
                'available': result.available,
                'exists': result.exists,
            }
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=f"Email '{email}' is {'available' if result.available else 'already taken'}"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Email check")


class HealthCheckView(APIView):  # Simplified - doesn't need BaseAPIView
    """Health check endpoint"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Check service health"""
        try:
            # Simple health check - no controller dependency
            return Response({
                "success": True,
                "message": "TCC API Service is healthy",
                "data": {
                    'status': 'healthy',
                    'service': 'tcc_api',
                    'timestamp': datetime.now().isoformat(),
                    'endpoints': {
                        'register': '/tcc/users/register/',
                        'login': '/tcc/auth/login/',
                        'health': '/tcc/health/',
                        'root': '/tcc/'
                    }
                }
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return Response({
                "success": False,
                "message": f"Service unhealthy: {str(e)}",
                "error": str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ============================================
# AUTHENTICATED USER ENDPOINTS
# ============================================

class ProfileView(BaseAPIView):
    """Current user profile management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        try:
            current_user = self.get_current_user(request)
            if not current_user:
                return Response({
                    "success": False,
                    "message": "Authentication required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            controller = self.get_controller()
            user_entity = self.call_async_method(
                controller.get_current_user_profile,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="Profile retrieved successfully"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Profile retrieval")
    
    def put(self, request):
        """Full update of current user profile"""
        return self._update_profile(request)
    
    def patch(self, request):
        """Partial update of current user profile"""
        return self._update_profile(request)
    
    def _update_profile(self, request):
        """Internal method to handle profile updates"""
        try:
            current_user = self.get_current_user(request)
            if not current_user:
                return Response({
                    "success": False,
                    "message": "Authentication required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            update_data = UserUpdateInputSchema(**request.data)
            controller = self.get_controller()
            
            user_entity = self.call_async_method(
                controller.update_current_user_profile,
                user_data=update_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="Profile updated successfully"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Profile update")


class UserListView(BaseAPIView):
    """List all users with pagination"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get paginated list of users"""
        try:
            current_user = self.get_current_user(request)
            page, per_page = get_pagination_params(request)
            
            query_data = UserQueryInputSchema(
                page=page,
                per_page=per_page,
                sort_by=request.query_params.get('sort_by', 'created_at'),
                sort_order=request.query_params.get('sort_order', 'desc')
            )
            
            controller = self.get_controller()
            users_entities, total_count = self.call_async_method(
                controller.get_all_users,
                validated_data=query_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            items = [entity_to_dict(entity) for entity in users_entities]
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            response_data = {
                'items': items,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=f"Found {total_count} users"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Get users")


# ============================================
# USER VIEWSET - Standard DRF
# ============================================

class UserViewSet(viewsets.ViewSet):
    """
    User CRUD operations using standard DRF ViewSet
    Provides list, create, retrieve, update, destroy actions
    """
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def get_current_user(self, request):
        """Get authenticated user"""
        return request.user if request.user.is_authenticated else None
    
    def get_context(self, request):
        """Build context for controller"""
        return build_context(request)
    
    def get_controller(self):
        """Get controller instance - handles both sync and async"""
        return safe_get_controller()
    
    def call_async_method(self, method, *args, **kwargs):
        """Call async controller method synchronously"""
        try:
            return async_to_sync(method)(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling async method {method.__name__}: {e}", exc_info=True)
            raise
    
    def list(self, request):
        """List all users with pagination"""
        try:
            current_user = self.get_current_user(request)
            page, per_page = get_pagination_params(request)
            
            query_data = UserQueryInputSchema(
                page=page,
                per_page=per_page,
                sort_by=request.query_params.get('sort_by', 'created_at'),
                sort_order=request.query_params.get('sort_order', 'desc')
            )
            
            controller = self.get_controller()
            users_entities, total_count = self.call_async_method(
                controller.get_all_users,
                validated_data=query_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            items = [entity_to_dict(entity) for entity in users_entities]
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            response_data = {
                'items': items,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=f"Found {total_count} users"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "List users")
    
    def create(self, request):
        """Create new admin user - Admin only"""
        try:
            current_user = self.get_current_user(request)
            if not current_user or not current_user.is_staff:
                return Response({
                    "success": False,
                    "message": "Admin privileges required"
                }, status=status.HTTP_403_FORBIDDEN)
            
            user_data = UserCreateInputSchema(**request.data)
            controller = self.get_controller()
            
            user_entity = self.call_async_method(
                controller.create_admin_user,
                user_data=user_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="Admin user created successfully",
                    status_code=status.HTTP_201_CREATED
                ).to_dict(),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return handle_exception(e, "Create admin user")
    
    def retrieve(self, request, pk=None):
        """Get user by ID"""
        try:
            current_user = self.get_current_user(request)
            if not current_user:
                return Response({
                    "success": False,
                    "message": "Authentication required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Parse and clean the ID
            user_id = self.parse_and_clean_id(pk)
            if user_id is None:
                return Response({
                    "success": False,
                    "message": f"Invalid user ID format: {pk}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            user_entity = self.call_async_method(
                controller.get_user_by_id,
                user_id=user_id,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="User retrieved successfully"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Get user by ID")

    def parse_and_clean_id(self, id_value):
        """Parse and clean ID values from various formats."""
        if id_value is None:
            return None
        
        try:
            # If already an int, return it
            if isinstance(id_value, int):
                return id_value
            
            # Convert to string and clean
            id_str = str(id_value)
            
            # Remove common formatting characters
            for char in ['{', '}', '[', ']', "'", '"', ' ', '\t', '\n']:
                id_str = id_str.replace(char, '')
            
            # Try to convert to int
            return int(id_str)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse ID: {id_value}")
            return None
    
    def update(self, request, pk=None):
        """Full update user by ID"""
        try:
            current_user = self.get_current_user(request)
            if not current_user:
                return Response({
                    "success": False,
                    "message": "Authentication required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            update_data = UserUpdateInputSchema(**request.data)
            controller = self.get_controller()
            
            user_entity = self.call_async_method(
                controller.update_user,
                user_id=int(pk),
                user_data=update_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="User updated successfully"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Update user")
    
    def partial_update(self, request, pk=None):
        """Partial update user by ID"""
        return self.update(request, pk)
    
    def destroy(self, request, pk=None):
        """Delete user - Admin only"""
        try:
            current_user = self.get_current_user(request)
            if not current_user or not current_user.is_staff:
                return Response({
                    "success": False,
                    "message": "Admin privileges required"
                }, status=status.HTTP_403_FORBIDDEN)
            
            controller = self.get_controller()
            success = self.call_async_method(
                controller.delete_user,
                user_id=int(pk),
                current_user=current_user,
                context=self.get_context(request)
            )
            
            if success:
                return Response(
                    APIResponse.create_success(
                        data={'deleted': True, 'user_id': pk},
                        message="User deleted successfully"
                    ).to_dict(),
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                raise DomainException("Failed to delete user")
                
        except Exception as e:
            return handle_exception(e, "Delete user")
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def by_email(self, request):
        """Get user by email - Admin only"""
        try:
            current_user = self.get_current_user(request)
            email = request.query_params.get('email')
            
            if not email:
                return Response({
                    "success": False,
                    "message": "Email parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            user_entity = self.call_async_method(
                controller.get_user_by_email,
                email=email,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="User retrieved successfully"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Get user by email")
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def search(self, request):
        """Search users by query string"""
        try:
            current_user = self.get_current_user(request)
            query = request.query_params.get('q', '')
            page, per_page = get_pagination_params(request)
            
            if not query:
                return Response({
                    "success": False,
                    "message": "Search query 'q' parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            users_entities, total_count = self.call_async_method(
                controller.search_users,
                query=query,
                page=page,
                per_page=per_page,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            items = [entity_to_dict(entity) for entity in users_entities]
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            response_data = {
                'items': items,
                'query': query,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=f"Found {total_count} users matching '{query}'"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "Search users")


# ============================================
# ROOT VIEW - Add at the end of file
# ============================================

class RootView(APIView):
    """Public API root endpoint"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return API information"""
        return Response({
            "success": True,
            "message": "TCC API Server",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/tcc/health/",
                "register": "/tcc/users/register/",
                "login": "/tcc/auth/login/",
                "profile": "/tcc/users/profile/",
                "check_email": "/tcc/users/check-email/",
                "auth": {
                    "login": "/tcc/auth/login/",
                    "logout": "/tcc/auth/logout/",
                    "refresh": "/tcc/auth/refresh/",
                    "verify": "/tcc/auth/verify/",
                    "forgot_password": "/tcc/auth/forgot-password/",
                    "reset_password": "/tcc/auth/reset-password/"
                }
            }
        })