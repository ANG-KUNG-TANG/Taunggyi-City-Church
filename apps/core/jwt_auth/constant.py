from enum import Enum

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class ErrorCode(str, Enum):
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"
    MISSING_TOKEN = "missing_token"
    INVALID_SIGNATURE = "invalid_signature"