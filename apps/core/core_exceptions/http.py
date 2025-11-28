from rest_framework import status
from rest_framework.exceptions import APIException

class BaseAPIException(APIException):
    """Base class for all API exceptions"""
    
    def __init__(self, detail=None, code=None, extra_data=None):
        super().__init__(detail, code)
        self.extra_data = extra_data or {}
        
        # Standardize error response format
        self.data = {
            'error': {
                'code': self.default_code,
                'message': self.detail,
                **self.extra_data
            }
        }

class ValidationException(BaseAPIException):
    """Validation exception for API requests"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'
    
    def __init__(self, detail=None, code=None, field_errors=None):
        extra_data = {'field_errors': field_errors or {}}
        super().__init__(detail, code, extra_data)

class AuthenticationException(BaseAPIException):
    """Authentication failed exception"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = 'authentication_failed'

class PermissionException(BaseAPIException):
    """Permission denied exception"""
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'

class NotFoundException(BaseAPIException):
    """Resource not found exception"""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'

class ServerException(BaseAPIException):
    """Internal server error exception"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = 'server_error'