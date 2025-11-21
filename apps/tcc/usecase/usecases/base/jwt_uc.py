from typing import List, Dict, Optional, Tuple
from apps.core.security.jwt_manager import JWTManager, TokenType
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from usecases.base.base_uc import BaseUseCase
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JWTCreateUseCase(BaseUseCase):
    """Enhanced UseCase for JWT creation with validation and business rules"""

    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager

    async def execute(self, 
                     user_id: str, 
                     email: str, 
                     roles: List[str] = None, 
                     permissions: List[str] = None, 
                     session_id: str = None) -> Dict:
        """
        Generates access and refresh tokens for a user with validation
        
        Args:
            user_id: Unique user identifier
            email: User email address
            roles: List of user roles
            permissions: List of user permissions
            session_id: Session identifier for tracking
            
        Returns:
            Dictionary containing tokens and metadata
            
        Raises:
            InvalidUserInputException: If input validation fails
        """
        # Input validation
        self._validate_input(user_id, email, roles, permissions)
        
        try:
            # Create access token
            access_token = self.jwt_manager.create_access_token(
                user_id=user_id,
                email=email,
                roles=roles,
                permissions=permissions,
                session_id=session_id
            )

            # Create refresh token
            refresh_token = self.jwt_manager.create_refresh_token(
                user_id=user_id,
                email=email,
                session_id=session_id
            )

            # Extract metadata from tokens for tracking
            access_payload = self.jwt_manager.get_token_metadata(access_token)
            refresh_payload = self.jwt_manager.get_token_metadata(refresh_token)

            result = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "access_jti": access_payload.get("jti"),
                "refresh_jti": refresh_payload.get("jti"),
                "token_type": "Bearer",
                "expires_in": self.jwt_manager.config.access_token_expiry,
                "expires_at": access_payload.get("expires_at"),
                "user_id": user_id,
                "session_id": session_id
            }
            
            logger.info(f"Tokens created successfully for user {user_id}, session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Token creation failed for user {user_id}: {e}")
            raise InvalidUserInputException(f"Failed to create tokens: {str(e)}")

    def _validate_input(self, 
                       user_id: str, 
                       email: str, 
                       roles: List[str] = None, 
                       permissions: List[str] = None):
        """Validate input parameters"""
        if not user_id or not isinstance(user_id, str):
            raise InvalidUserInputException("Valid user_id is required")
        
        if not email or not isinstance(email, str):
            raise InvalidUserInputException("Valid email is required")
        
        if roles and not isinstance(roles, list):
            raise InvalidUserInputException("Roles must be a list")
        
        if permissions and not isinstance(permissions, list):
            raise InvalidUserInputException("Permissions must be a list")


class JWTVerifyUseCase(BaseUseCase):
    """UseCase for JWT token verification and validation"""

    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager

    async def execute(self, 
                     token: str, 
                     token_type: TokenType = None,
                     expected_roles: List[str] = None,
                     expected_permissions: List[str] = None) -> Dict:
        """
        Verify JWT token and validate claims
        
        Args:
            token: JWT token string
            token_type: Expected token type for validation
            expected_roles: Required roles for authorization
            expected_permissions: Required permissions for authorization
            
        Returns:
            Dictionary with verification result and payload
            
        Raises:
            InvalidUserInputException: If token is invalid or authorization fails
        """
        if not token:
            raise InvalidUserInputException("Token is required")

        try:
            # Verify token signature and basic claims
            is_valid, payload = self.jwt_manager.verify_token(token, token_type)
            
            if not is_valid or not payload:
                raise InvalidUserInputException("Invalid or expired token")

            # Extract token metadata for additional validation
            token_metadata = self.jwt_manager.get_token_metadata(token)
            
            # Validate authorization claims
            self._validate_authorization(payload, expected_roles, expected_permissions)

            result = {
                "is_valid": True,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "token_type": payload.get("token_type"),
                "jti": payload.get("jti"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "session_id": payload.get("session_id"),
                "expires_at": token_metadata.get("expires_at"),
                "issued_at": token_metadata.get("issued_at")
            }
            
            logger.info(f"Token verified successfully for user {payload.get('sub')}")
            return result
            
        except InvalidUserInputException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise InvalidUserInputException(f"Token verification failed: {str(e)}")

    def _validate_authorization(self, 
                              payload: Dict, 
                              expected_roles: List[str] = None,
                              expected_permissions: List[str] = None):
        """Validate role-based and permission-based authorization"""
        token_roles = set(payload.get("roles", []))
        token_permissions = set(payload.get("permissions", []))
        
        # Validate roles if required
        if expected_roles:
            required_roles = set(expected_roles)
            if not required_roles.intersection(token_roles):
                raise InvalidUserInputException("Insufficient roles")
        
        # Validate permissions if required
        if expected_permissions:
            required_permissions = set(expected_permissions)
            if not required_permissions.issubset(token_permissions):
                raise InvalidUserInputException("Insufficient permissions")


class JWTRefreshUseCase(BaseUseCase):
    """UseCase for refreshing JWT tokens"""

    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager

    async def execute(self, refresh_token: str) -> Dict:
        """
        Refresh access token using valid refresh token
        
        Args:
            refresh_token: Valid refresh token string
            
        Returns:
            Dictionary with new access token and metadata
            
        Raises:
            InvalidUserInputException: If refresh token is invalid
        """
        if not refresh_token:
            raise InvalidUserInputException("Refresh token is required")

        try:
            # Verify refresh token
            verify_uc = JWTVerifyUseCase(self.jwt_manager)
            verification_result = await verify_uc.execute(
                refresh_token, 
                TokenType.REFRESH
            )
            
            if not verification_result["is_valid"]:
                raise InvalidUserInputException("Invalid refresh token")

            user_id = verification_result["user_id"]
            email = verification_result["email"]
            session_id = verification_result["session_id"]
            roles = verification_result["roles"]
            permissions = verification_result["permissions"]

            # Create new access token
            create_uc = JWTCreateUseCase(self.jwt_manager)
            tokens = await create_uc.execute(
                user_id=user_id,
                email=email,
                roles=roles,
                permissions=permissions,
                session_id=session_id
            )

            # Return new access token (keep the same refresh token)
            result = {
                "access_token": tokens["access_token"],
                "refresh_token": refresh_token,  # Keep original refresh token
                "access_jti": tokens["access_jti"],
                "refresh_jti": verification_result["jti"],
                "token_type": "Bearer",
                "expires_in": self.jwt_manager.config.access_token_expiry,
                "expires_at": tokens["expires_at"],
                "user_id": user_id,
                "session_id": session_id
            }
            
            logger.info(f"Token refreshed successfully for user {user_id}")
            return result
            
        except InvalidUserInputException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise InvalidUserInputException(f"Token refresh failed: {str(e)}")


class JWTRevokeUseCase(BaseUseCase):
    """UseCase for token revocation (client-side)"""
    
    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager

    async def execute(self, token: str) -> Dict:
        """
        Validate token and return revocation information
        Note: Actual revocation should be handled at storage layer
        
        Args:
            token: Token to be revoked
            
        Returns:
            Dictionary with revocation metadata
        """
        try:
            # Extract token metadata before any operations
            token_metadata = self.jwt_manager.get_token_metadata(token)
            
            result = {
                "jti": token_metadata.get("jti"),
                "user_id": token_metadata.get("user_id"),
                "token_type": token_metadata.get("token_type"),
                "revoked_at": datetime.utcnow(),
                "message": "Token should be added to revocation list"
            }
            
            logger.info(f"Token revocation requested for jti {result['jti']}")
            return result
            
        except Exception as e:
            logger.error(f"Token revocation processing failed: {e}")
            raise InvalidUserInputException(f"Token revocation failed: {str(e)}")


class JWTTokenInfoUseCase(BaseUseCase):
    """UseCase for extracting token information without verification"""
    
    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager

    async def execute(self, token: str) -> Dict:
        """
        Extract token information for debugging and monitoring
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with token metadata
        """
        if not token:
            raise InvalidUserInputException("Token is required")

        try:
            token_metadata = self.jwt_manager.get_token_metadata(token)
            
            result = {
                "jti": token_metadata.get("jti"),
                "user_id": token_metadata.get("user_id"),
                "email": token_metadata.get("email"),
                "token_type": token_metadata.get("token_type"),
                "roles": token_metadata.get("roles", []),
                "permissions": token_metadata.get("permissions", []),
                "session_id": token_metadata.get("session_id"),
                "issued_at": token_metadata.get("issued_at"),
                "expires_at": token_metadata.get("expires_at"),
                "is_expired": token_metadata.get("expires_at") < datetime.utcnow() 
                if token_metadata.get("expires_at") else None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Token info extraction failed: {e}")
            raise InvalidUserInputException(f"Token info extraction failed: {str(e)}")