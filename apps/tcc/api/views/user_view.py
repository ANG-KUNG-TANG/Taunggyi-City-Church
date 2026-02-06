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
    
    # Handle UserAlreadyExistsException with a clean message
    if isinstance(e, UserAlreadyExistsException):
        # Extract email from exception if available
        email = getattr(e, 'email' ,'Unknown')
        # Log at WARNING level since this is a user error, not a system error
        logger.warning(f"User registration failed: User with email '{email}' already exists")
        return Response({
            "success": False,
            "message": f"User with email '{email}' already exists",
            "error_code": "USER_ALREADY_EXISTS",
            "status_code": 409
        }, status=409)
    
        
    # Handle DomainValidationException
    elif isinstance(e, DomainValidationException):
        return Response({
            "success": False,
            "message": str(e),
            "error_code": "VALIDATION_ERROR",
            "status_code": 400
        }, status=400)
    
    # Handle UserNotFoundException
    elif isinstance(e, UserNotFoundException):
        return Response({
            "success": False,
            "message": str(e),
            "error_code": "USER_NOT_FOUND",
            "status_code": 404
        }, status=404)
    
    # Handle other exceptions
    else:
        logger.error(f"Unexpected {operation} error: {e}", exc_info=True)
        return Response({
            "success": False,
            "message": f"An error occurred during {operation}",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500
        }, status=500)


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
    """User registration endpoints"""
    
    # Public endpoint - normal user registration
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Register a new normal user - Public endpoint"""
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
            return handle_exception(e, "registration")
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def create_by_admin(self, request):
        """Create user with specified role - Admin only"""
        try:
            current_user = self.get_current_user(request)
            if not current_user or not current_user.is_staff:
                return Response({
                    "success": False,
                    "message": "Admin privileges required"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Extract role from request data (default to 'staff')
            role = request.data.get('role', 'staff').lower()
            
            # Validate role
            valid_roles = ['staff', 'admin']
            if role not in valid_roles:
                return Response({
                    "success": False,
                    "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Optional: Check for super admin privileges for creating admin users
            if role == 'admin':
                if hasattr(current_user, 'is_superuser') and not current_user.is_superuser:
                    return Response({
                        "success": False,
                        "message": "Super admin privileges required to create admin users"
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate and parse user data
            user_data = UserCreateInputSchema(**request.data)
            controller = self.get_controller()
            
            # Choose controller method based on role
            if role == 'staff':
                controller_method = controller.create_staff_user
                success_message = "Staff user created successfully"
            else:  # role == 'admin'
                controller_method = controller.create_admin_user
                success_message = "Admin user created successfully"
            
            # Execute the controller method
            user_entity = self.call_async_method(
                controller_method,
                user_data=user_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message=success_message,
                    status_code=status.HTTP_201_CREATED
                ).to_dict(),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            role = request.data.get('role', 'staff')
            return handle_exception(e, f"create {role} user")
        
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
           
            # Create EmailCheckInputSchema instance
            email_check_data = EmailCheckInputSchema(email=email)
            
            controller = self.get_controller()
            
            # Call the controller method
            result = self.call_async_method(
                controller.check_email_availability,
                validated_data=email_check_data,
                context=self.get_context(request)
            )
            
            # Handle the response - it should be a dict now
            if isinstance(result, dict):
                response_data = {
                    'email': result.get('email', email),
                    'available': result.get('available', False),
                    'exists': result.get('exists', False),
                }
            else:
                # Fallback if it's not a dict
                response_data = {
                    'email': email,
                    'available': False,
                    'exists': False,
                }
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=f"Email '{email}' is {'available' if response_data['available'] else 'already taken'}"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "email check")
        
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
            return handle_exception(e, "profile retrieval")
    
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
            return handle_exception(e, "profile update")


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
            result = self.call_async_method(
                controller.get_all_users,
                validated_data=query_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            # Handle both possible return types:
            # 1. Tuple of (users_entities, total_count)
            # 2. Single value that might be a list or dict
            if isinstance(result, tuple) and len(result) == 2:
                users_entities, total_count = result
            elif isinstance(result, dict) and 'items' in result and 'total' in result:
                # If the controller returns a dict with items and total
                users_entities = result.get('items', [])
                total_count = result.get('total', 0)
            else:
                # Assume result is just the list of entities
                users_entities = result if isinstance(result, list) else []
                total_count = len(users_entities)
            
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
            return handle_exception(e, "get users")

class GetyByid(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        """
        Get user by ID
        Supports both:
        - Query parameter: /api/users/by-id/?id=123
        - Path parameter: /api/users/123/ (if configured)
        """
        try:
            # Try to get user_id from path parameter first
            if user_id is None:
                # Fall back to query parameter
                user_id = request.query_params.get('id')
            
            if not user_id:
                return Response(
                    {
                        "success": False,
                        "message": "User ID is required. Use ?id=123 or path parameter",
                        "example_usage": {
                            "query_param": "/api/users/by-id/?id=123",
                            "path_param": "/api/users/123/"
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert to int if it's a string
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return Response(
                    {
                        "success": False,
                        "message": "Invalid user ID format",
                        "provided_id": user_id
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get current user from authentication
            current_user = self.get_current_user(request)
            if not current_user:
                return Response(
                    {"success": False, "message": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # IMPORTANT: Users can only view their own profile unless they're admin
            # Check if current user is trying to view their own profile
            # You need to get the current user's ID from the token/authentication
            current_user_id = self.get_current_user_id(request)  # You need to implement this
            
            # If not admin and trying to view another user, deny access
            if not self.is_admin(request) and current_user_id != user_id:
                return Response(
                    {
                        "success": False,
                        "message": "Insufficient permissions to view this user",
                        "detail": "Users can only view their own profile. Admins can view any user.",
                        "requested_user_id": user_id,
                        "your_user_id": current_user_id
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            controller = self.get_controller()
            user_entity = self.call_async_method(
                controller.get_user_by_id,
                user_id=user_id,
                current_user=current_user,  # Pass the authenticated user object
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message="User retrieved successfully"
                ).to_dict()
            )
        except DomainValidationException as e:
            # Handle domain validation exceptions (like permission errors)
            if "Insufficient permissions" in str(e):
                return Response(
                    {
                        "success": False,
                        "message": str(e),
                        "detail": "You don't have permission to view this user's profile"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            return handle_exception(e, "user retrieval")
        except Exception as e:
            return handle_exception(e, "user retrieval")
    
    def get_current_user_id(self, request):
        """Extract current user's ID from the request"""
        # Assuming your authentication stores user ID in request.user or similar
        if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
            return request.user.id
        elif hasattr(request, 'auth') and request.auth:
            # Try to get from token payload
            return request.auth.get('user_id')
        return None
    
    def is_admin(self, request):
        """Check if current user is admin"""
        if hasattr(request, 'user') and request.user:
            # Check user roles - adjust based on your user model
            return hasattr(request.user, 'is_admin') and request.user.is_admin
        return False
        
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
    
    def get_user_by_id(self, request, id=None):
        """Get user by ID endpoint"""
        view = GetyByid()
        return view.get(request, user_id=id)
    
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
            result = self.call_async_method(
                controller.get_all_users,
                validated_data=query_data,
                current_user=current_user,
                context=self.get_context(request)
            )
            

            if isinstance(result, tuple) and len(result) == 2:
                users_entities, total_count = result
            elif isinstance(result, dict) and 'items' in result and 'total' in result:
                # If the controller returns a dict with items and total
                users_entities = result.get('items', [])
                total_count = result.get('total', 0)
            else:
                # Assume result is just the list of entities
                users_entities = result if isinstance(result, list) else []
                total_count = len(users_entities)
            
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
            return handle_exception(e, "list users")
    
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
            return handle_exception(e, "create admin user")
    
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
            return handle_exception(e, "get user by ID")

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
            return handle_exception(e, "update user")
    
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
            return handle_exception(e, "delete user")
    
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
            return handle_exception(e, "get user by email")
    
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
            return handle_exception(e, "search users")
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def by_role(self, request):
        """Get users by role - Admin only"""
        try:
            current_user = self.get_current_user(request)
            role = request.query_params.get('role')
            page, per_page = get_pagination_params(request)
            
            if not role:
                return Response({
                    "success": False,
                    "message": "Role parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            users_entities, total_count = self.call_async_method(
                controller.get_users_by_role,
                role=role,
                page=page,
                per_page=per_page,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            items = [entity_to_dict(entity) for entity in users_entities]
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            
            response_data = {
                'items': items,
                'role': role,
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
                    message=f"Found {total_count} users with role '{role}'"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "get users by role")

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def change_status(self, request, pk=None):
        """Change user status - Admin only"""
        try:
            current_user = self.get_current_user(request)
            if not current_user or not current_user.is_staff:
                return Response({
                    "success": False,
                    "message": "Admin privileges required"
                }, status=status.HTTP_403_FORBIDDEN)
            
            status_value = request.data.get('status')
            if not status_value:
                return Response({
                    "success": False,
                    "message": "Status parameter is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            
            user_entity = self.call_async_method(
                controller.change_user_status,
                user_id=int(pk),
                status=status_value,
                current_user=current_user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=entity_to_dict(user_entity),
                    message=f"User status changed to {status_value}"
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "change user status")

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_delete(self, request):
        """Bulk delete users - Admin only"""
        try:
            current_user = self.get_current_user(request)
            if not current_user or not current_user.is_staff:
                return Response({
                    "success": False,
                    "message": "Admin privileges required"
                }, status=status.HTTP_403_FORBIDDEN)
            
            user_ids = request.data.get('user_ids', [])
            if not user_ids:
                return Response({
                    "success": False,
                    "message": "User IDs are required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            
            # Since controller doesn't have bulk_delete_users method,
            # we'll implement it by looping through individual deletes
            deleted_count = 0
            failed_ids = []
            
            for user_id in user_ids:
                try:
                    success = self.call_async_method(
                        controller.delete_user,
                        user_id=int(user_id),
                        current_user=current_user,
                        context=self.get_context(request)
                    )
                    if success:
                        deleted_count += 1
                    else:
                        failed_ids.append(user_id)
                except Exception as e:
                    failed_ids.append(user_id)
                    logger.error(f"Failed to delete user {user_id}: {e}")
            
            response_data = {
                'total_requested': len(user_ids),
                'deleted_count': deleted_count,
                'failed_count': len(failed_ids),
                'failed_ids': failed_ids
            }
            
            if deleted_count == len(user_ids):
                message = f"Successfully deleted all {deleted_count} users"
            else:
                message = f"Deleted {deleted_count} out of {len(user_ids)} users. Failed: {len(failed_ids)}"
            
            return Response(
                APIResponse.create_success(
                    data=response_data,
                    message=message
                ).to_dict()
            )
        except Exception as e:
            return handle_exception(e, "bulk delete users")
