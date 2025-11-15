class JWTException(Exception):
    """Base JWT exception"""
    default_message = "JWT authentication failed"
    
    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)

class TokenExpiredError(JWTException):
    default_message = "Token has expired"

class InvalidTokenError(JWTException):
    default_message = "Invalid token"

class MissingTokenError(JWTException):
    default_message = "Authentication token is missing"