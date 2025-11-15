import jwt
import uuid
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from apps.tcc.models.base.mixion import User


from ..config import JWTConfig
from ..schemas import TokenPayload, TokenPair, TokenType
from ..exceptions import TokenExpiredError, InvalidTokenError
from ..models import RefreshToken

class TokenService:
    @staticmethod
    def create_token_pair(user: User) -> TokenPair:
        """Create access and refresh token pair for user"""
        access_token = TokenService._create_access_token(user)
        refresh_token = TokenService._create_refresh_token(user)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWTConfig.ACCESS_TOKEN_LIFETIME
        )
    
    @staticmethod
    def _create_access_token(user: User) -> str:
        """Create access token with user claims"""
        now = timezone.now()
        expires_at = now + timedelta(seconds=JWTConfig.ACCESS_TOKEN_LIFETIME)
        
        payload = TokenPayload(
            iss=JWTConfig.ISSUER,
            sub=str(user.id),
            aud=JWTConfig.AUDIENCE,
            exp=int(expires_at.timestamp()),
            iat=int(now.timestamp()),
            jti=str(uuid.uuid4()),
            typ=TokenType.ACCESS,
            user_id=user.id,
            email=user.email
        )
        
        return jwt.encode(
            payload.dict(),
            JWTConfig.ACCESS_SECRET,
            algorithm=JWTConfig.ALGORITHM
        )
    
    @staticmethod
    def validate_access_token(token: str) -> TokenPayload:
        """Validate and decode access token"""
        try:
            payload_dict = jwt.decode(
                token,
                JWTConfig.ACCESS_SECRET,
                algorithms=[JWTConfig.ALGORITHM],
                audience=JWTConfig.AUDIENCE,
                issuer=JWTConfig.ISSUER
            )
            
            return TokenPayload(**payload_dict)
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(str(e))
    
    @staticmethod
    def _create_refresh_token(user: User) -> str:
        """Create and store refresh token (basic implementation)"""
        # For minimal version, we'll just create a simple refresh token
        # In production, you'd want to hash and store this
        refresh_payload = {
            'user_id': user.id,
            'jti': str(uuid.uuid4()),
            'exp': int((timezone.now() + timedelta(seconds=JWTConfig.REFRESH_TOKEN_LIFETIME)).timestamp()),
            'type': 'refresh'
        }
        
        return jwt.encode(
            refresh_payload,
            JWTConfig.REFRESH_SECRET,
            algorithm=JWTConfig.ALGORITHM
        )