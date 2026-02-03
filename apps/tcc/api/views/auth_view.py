"""
Authentication Views - Standard DRF
Handles login, logout, token refresh, password reset
"""
import logging
import inspect
from pydantic import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser
from asgiref.sync import async_to_sync

from apps.core.schemas.input_schemas.auth import (
    LoginInputSchema,
    RefreshTokenInputSchema,
    VerifyTokenInputSchema, 
    ForgotPasswordInputSchema,
    ResetPasswordInputSchema,
)
from apps.core.schemas.common.response import APIResponse
from apps.tcc.api.views.base_view import build_context
from apps.tcc.usecase.domain_exception.u_exceptions import AccountLockedException, InvalidUserInputException
from apps.tcc.usecase.services.auth.auth_controller import AuthController
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    AccountInactiveException,
    InvalidCredentialsException,
    TokenExpiredException,
    InvalidTokenException,
)
from apps.core.core_exceptions.domain import DomainValidationException

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTION
# ============================================

def safe_get_auth_controller():
    """
    Safely get auth controller instance, handling both sync and async factories
    """
    try:
        from apps.tcc.usecase.services.auth.auth_controller import create_auth_controller
        
        # Get controller (might be async factory)
        controller_factory = create_auth_controller
        
        # If it's a coroutine or async function, await it
        if inspect.iscoroutinefunction(controller_factory):
            controller = async_to_sync(controller_factory)()
        else:
            controller = controller_factory()
        
        return controller
    except Exception as e:
        logger.error(f"Failed to get auth controller: {e}", exc_info=True)
        # Fallback to direct instantiation
        try:
            from apps.tcc.usecase.services.auth.auth_controller import AuthController
            return AuthController()
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise


# ============================================
# BASE AUTH VIEW
# ============================================

class BaseAuthView(APIView):
    """Base view for authentication endpoints"""
    parser_classes = [JSONParser]
    
    def get_context(self, request):
        """Build context for controller"""
        return build_context(request)
    
    def get_controller(self):
        """Get auth controller instance - handles both sync and async"""
        return safe_get_auth_controller()
    
    def call_async_method(self, method, *args, **kwargs):
        """Call async controller method synchronously"""
        try:
            return async_to_sync(method)(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling async method {method.__name__}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def format_exception_message(e: Exception) -> str:
        """Format exception message for user consumption"""
        # Priority 1: user_message attribute
        if hasattr(e, 'user_message') and e.user_message:
            return str(e.user_message)
        
        # Priority 2: Check for common patterns in the string
        error_str = str(e)
        
        # Remove technical details like operation IDs
        import re
        # Remove patterns like "(ID: xxx-xxx-xxx)"
        error_str = re.sub(r'\(ID: [a-f0-9\-]+\)', '', error_str)
        
        # Remove exception class names in brackets
        error_str = re.sub(r'\[[A-Z_]+\]\s*', '', error_str)
        
        # Clean up extra spaces
        error_str = error_str.strip()
        
        # If empty after cleaning, use generic message
        if not error_str:
            return "An error occurred during authentication"
        
        return error_str
    
    def handle_auth_exception(self, e: Exception, operation: str) -> Response:
        """Handle authentication-specific exceptions"""
        logger.error(f"{operation} error type: {type(e).__name__}")
        
        # Check for specific attributes first
        if hasattr(e, 'user_message'):
            message = self.format_exception_message(e)
        else:
            message = str(e)
        
        # Determine error code and status
        error_mapping = {
            'InvalidAuthInputException': ("INVALID_CREDENTIALS", 400),
            'InvalidCredentialsException': ("INVALID_CREDENTIALS", 401),
            'TokenExpiredException': ("TOKEN_EXPIRED", 401),
            'InvalidTokenException': ("INVALID_TOKEN", 401),
            'DomainValidationException': ("VALIDATION_ERROR", 400),
            'AccountLockedException': ("ACCOUNT_LOCKED", 403),
            'AccountInactiveException': ("ACCOUNT_INACTIVE", 403),
        }
        
        error_code, status_code = error_mapping.get(
            type(e).__name__, 
            ("INTERNAL_ERROR", 500)
        )
        
        # Build response
        response_data = {
            "success": False,
            "message": message,
            "error_code": error_code
        }
        
        # Add field errors if they exist
        if hasattr(e, 'field_errors'):
            response_data["field_errors"] = e.field_errors
        
        return Response(response_data, status=status_code)
    
    def _get_exception_type_name(self, e: Exception) -> str:
        """Get the simple name of the exception class"""
        return type(e).__name__

    def _is_auth_exception(self, e: Exception) -> bool:
        """Check if the exception is an authentication exception"""
        auth_exceptions = [
            'InvalidAuthInputException', 'InvalidCredentialsException',
            'TokenExpiredException', 'InvalidTokenException',
            'AccountLockedException', 'AccountInactiveException'
        ]
        return self._get_exception_type_name(e) in auth_exceptions

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

class LoginView(BaseAuthView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Validate input
            login_data = LoginInputSchema(**request.data)
            controller = self.get_controller()
            
            # Convert Pydantic model to dict for controller
            login_dict = login_data.dict()
            
            # Call controller method
            auth_result = self.call_async_method(
                controller.login,
                input_data=login_dict,  # Changed from credentials to input_data
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=auth_result,
                    message="Login successful"
                ).to_dict()
            )
        except Exception as e:
            logger.error(f"LoginView caught exception: {type(e).__name__}")
            logger.error(f"Exception attributes: {dir(e)}")
            if hasattr(e, 'user_message'):
                logger.error(f"Exception user_message: {e.user_message}")
            if hasattr(e, 'field_errors'):
                logger.error(f"Exception field_errors: {e.field_errors}")
            
            return self.handle_auth_exception(e, "Login")


class LogoutView(BaseAuthView):
    """User logout endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
      
        try:
            # Validate input
            logger.info(f"Attempting to validate login data: {request.data}")
            login_data = LoginInputSchema(**request.data)
            
            controller = self.get_controller()

            login_dict = login_data.dict()
            logger.info(f"Login dict: {login_dict.keys()}")
            
            # Call controller method
            logger.info(f"Calling controller.login()...")
            auth_result = self.call_async_method(
                controller.login,
                input_data=login_dict,
                context=self.get_context(request)
            )
            logger.info(f"Controller.login() completed successfully")
            
            return Response(
                APIResponse.create_success(
                    data=auth_result,
                    message="Login successful"
                ).to_dict()
            )
        except Exception as e:
            logger.error(f"LoginView error details:", exc_info=True)
            return self.handle_auth_exception(e, "Login")

class RefreshTokenView(BaseAuthView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(f"Refresh token request received. Headers: {request.headers}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Request data type: {type(request.data)}")
        
        # Handle both field names
        data = request.data.copy()
        
        # Debug: Log all keys
        logger.info(f"All keys in request data: {list(data.keys())}")
        
        # Handle multiple field names
        if 'refresh' in data and 'refresh_token' not in data:
            logger.info(f"Mapping 'refresh' to 'refresh_token'. Value: {data['refresh'][:20]}...")
            data['refresh_token'] = data['refresh']
        elif 'refreshToken' in data and 'refresh_token' not in data:
            logger.info(f"Mapping 'refreshToken' to 'refresh_token'. Value: {data['refreshToken'][:20]}...")
            data['refresh_token'] = data['refreshToken']
        
        logger.info(f"Final data being sent to schema: {data}")
        
        try:
            refresh_data = RefreshTokenInputSchema(**data)
            logger.info(f"Schema validation successful. Parsed data: {refresh_data}")
            
            # FIXED: Use refresh_data.refresh_token instead of refresh_data.actual_refresh_token
            if not refresh_data.refresh_token:
                return Response({
                    "success": False,
                    "error": {
                        "code": "REFRESH_TOKEN_REQUIRED",
                        "message": "Refresh token is required"
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            token_result = self.call_async_method(
                controller.refresh_token,
                input_data={'refresh_token': refresh_data.refresh_token},  # FIXED: Use refresh_data.refresh_token
                context=self.get_context(request)
            )

            return Response(
                APIResponse.create_success(
                    data=token_result,
                    message="Token refreshed successfully"
                ).to_dict(),
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            logger.error(f"Validation error: {e.errors()}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid refresh token format",
                        "details": e.errors()
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error in refresh token: {e}", exc_info=True)
            return self.handle_auth_exception(e, "Token refresh")
#====================================
# DEbug vrefres view
#====================================

class DebugRefreshView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        return Response({
            "request_data": request.data,
            "request_headers": dict(request.headers),
            "request_content_type": request.content_type,
            "keys_in_data": list(request.data.keys()),
            "refresh_value": request.data.get('refresh'),
            "refresh_token_value": request.data.get('refresh_token'),
            "refreshToken_value": request.data.get('refreshToken'),
        })
    
class VerifyTokenView(BaseAuthView):  
    """Token verification endpoint"""
    authentication_classes = []  # Disable JWT authentication
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Verify if a token is valid
        
        Request body:
        {
            "access_token": "..."
        }
        
        Response:
        {
            "success": true,
            "data": {
                "valid": true,
                "user_id": 123,
                "expires_at": "2024-01-01T00:00:00Z"
            }
        }
        """
        try:
            controller = self.get_controller()
            
            verification_result = self.call_async_method(
                controller.verify_token,
                input_data=request.data,  # Pass the raw request data
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=verification_result,
                    message="Token is valid" if verification_result.get('valid') else "Token is invalid"
                ).to_dict()
            )
        except Exception as e:
            return self.handle_auth_exception(e, "Token verification")

class ForgotPasswordView(BaseAuthView):
    """Forgot password endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Request password reset
        
        Request body:
        {
            "email": "user@example.com"
        }
        
        Response:
        {
            "success": true,
            "message": "Password reset email sent"
        }
        """
        try:
            forgot_data = ForgotPasswordInputSchema(**request.data)
            controller = self.get_controller()
            
            result = self.call_async_method(
                controller.forgot_password,
                input_data=forgot_data.dict(),  # FIX: Use input_data parameter
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=result,
                    message="If the email exists, a password reset link has been sent"
                ).to_dict()
            )
        except Exception as e:
            # Don't reveal if email exists or not for security
            logger.error(f"Forgot password error: {e}")
            return Response(
                APIResponse.create_success(
                    data={'email_sent': False},
                    message="If the email exists, a password reset link has been sent"
                ).to_dict()
            )


class ResetPasswordView(BaseAuthView):
    """Reset password endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Reset password with token
        
        Request body:
        {
            "token": "...",
            "new_password": "newpassword123"
        }
        
        Response:
        {
            "success": true,
            "message": "Password reset successful"
        }
        """
        try:
            reset_data = ResetPasswordInputSchema(**request.data)
            controller = self.get_controller()
            
            result = self.call_async_method(
                controller.reset_password,
                input_data=reset_data.dict(),  # FIX: Use input_data parameter
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=result,
                    message="Password reset successful"
                ).to_dict()
            )
        except Exception as e:
            return self.handle_auth_exception(e, "Password reset")


class ChangePasswordView(BaseAuthView):
    """Change password for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Change current user's password
        
        Request body:
        {
            "current_password": "oldpassword",
            "new_password": "newpassword123"
        }
        
        Response:
        {
            "success": true,
            "message": "Password changed successfully"
        }
        """
        try:
            current_password = request.data.get('current_password')
            new_password = request.data.get('new_password')
            
            if not current_password or not new_password:
                return Response({
                    "success": False,
                    "message": "Both current_password and new_password are required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            controller = self.get_controller()
            
            result = self.call_async_method(
                controller.change_password,  # NOTE: This method doesn't exist in auth_controller.py
                input_data={
                    'current_password': current_password,
                    'new_password': new_password
                },
                current_user=request.user,
                context=self.get_context(request)
            )
            
            return Response(
                APIResponse.create_success(
                    data=result,
                    message="Password changed successfully"
                ).to_dict()
            )
        except Exception as e:
            return self.handle_auth_exception(e, "Change password")


# ============================================
# UTILITY VIEWS
# ============================================

class AuthStatusView(BaseAuthView):
    """Check authentication status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get current authentication status
        
        Response:
        {
            "success": true,
            "data": {
                "authenticated": true,
                "user_id": 123,
                "username": "john_doe",
                "email": "john@example.com"
            }
        }
        """
        try:
            user = request.user
            
            user_data = {
                'authenticated': True,
                'user_id': user.id,
                'username': getattr(user, 'username', None),
                'email': getattr(user, 'email', None),
                'is_staff': getattr(user, 'is_staff', False),
                'is_active': getattr(user, 'is_active', True),
            }
            
            return Response(
                APIResponse.create_success(
                    data=user_data,
                    message="Authenticated"
                ).to_dict()
            )
        except Exception as e:
            logger.error(f"Auth status error: {e}")
            return Response({
                "success": False,
                "message": "Unable to retrieve auth status"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
