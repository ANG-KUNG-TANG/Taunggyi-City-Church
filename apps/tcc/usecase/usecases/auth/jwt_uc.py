from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from apps.core.jwt.jwt_manager import JWTManager, TokenType
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
# from apps.core.schemas.common.response import TokenSchema
import logging
import uuid

logger = logging.getLogger(__name__)

class JWTCreateUseCase(BaseUseCase):
    """
    UseCase Responsibility: Generate JWT tokens according to business rules.
    
    Key Principle: All token logic belongs in the UseCase, not in Controller or View.
    
    Responsibilities:
    - Token type management (access, refresh, reset password, email verification)
    - Expiration policies enforcement
    - Token rotation and reuse rules
    - Blacklist checks (optional)
    - Business rule validation for token generation
    """
    
    def __init__(self, jwt_manager: JWTManager):
        super().__init__()
        self.jwt_manager = jwt_manager
        self._setup_token_policies()

    def _setup_token_policies(self):
        """Define token expiration policies according to business rules"""
        self.token_policies = {
            TokenType.ACCESS: {
                'expiry': timedelta(minutes=15),  # Short-lived for security
                'allowed_claims': ['sub', 'email', 'roles', 'permissions', 'session_id', 'token_type'],
                'require_session': False
            },
            TokenType.REFRESH: {
                'expiry': timedelta(days=7),  # Longer-lived for session persistence
                'allowed_claims': ['sub', 'email', 'session_id', 'token_type'],
                'require_session': True,
                'rotation_required': True  # Refresh tokens should be rotated
            },
            TokenType.RESET_PASSWORD: {
                'expiry': timedelta(hours=1),  # Short-lived for security
                'allowed_claims': ['sub', 'email', 'token_type', 'purpose'],
                'require_session': False,
                'single_use': True  # One-time use only
            },
            TokenType.EMAIL_VERIFICATION: {
                'expiry': timedelta(hours=24),  # Longer for user convenience
                'allowed_claims': ['sub', 'email', 'token_type', 'purpose'],
                'require_session': False,
                'single_use': True
            }
        }

    async def execute(self, 
                     user_id: str,
                     email: str,
                     token_type: TokenType = TokenType.ACCESS,
                     roles: List[str] = None,
                     permissions: List[str] = None,
                     session_id: str = None,
                     purpose: str = None,
                     previous_token_jti: str = None) -> Dict[str, Any]:
        """
        Generate JWT tokens according to business rules.
        
        Args:
            user_id: Unique user identifier
            email: User email for identification
            token_type: Type of token to generate (access, refresh, reset, verification)
            roles: User roles for authorization
            permissions: User permissions for fine-grained access
            session_id: Session identifier for tracking and revocation
            purpose: Specific purpose for special tokens (e.g., 'password_reset')
            previous_token_jti: JTI of previous token for rotation validation
            
        Returns:
            Dictionary containing tokens and metadata according to business rules
            
        Raises:
            InvalidUserInputException: When business rules are violated
        """
        # Input validation and business rule enforcement
        await self._validate_token_creation_rules(
            user_id, email, token_type, session_id, previous_token_jti
        )

        # Apply token-specific business rules
        claims = await self._build_token_claims(
            user_id, email, token_type, roles, permissions, session_id, purpose
        )

        try:
            # Generate token based on type
            token = await self._generate_token_by_type(token_type, claims)
            
            # Extract metadata for tracking and validation
            token_metadata = self._extract_token_metadata(token, token_type)
            
            # Apply post-generation rules (rotation, blacklist checks)
            await self._apply_post_generation_rules(token_type, token_metadata, previous_token_jti)
            
            logger.info(f"Token generated successfully: type={token_type}, user={user_id}, session={session_id}")
            return self._format_token_response(token, token_metadata, token_type)
            
        except Exception as e:
            logger.error(f"Token generation failed: {str(e)}")
            raise InvalidUserInputException(f"Token generation failed: {str(e)}")

    async def _validate_token_creation_rules(self,
                                           user_id: str,
                                           email: str,
                                           token_type: TokenType,
                                           session_id: str,
                                           previous_token_jti: str):
        """Enforce business rules for token creation"""
        
        # Rule 1: User ID and email are required for all token types
        if not user_id or not email:
            raise InvalidUserInputException("User ID and email are required for token generation")
        
        # Rule 2: Session ID is required for refresh tokens
        policy = self.token_policies.get(token_type, {})
        if policy.get('require_session') and not session_id:
            raise InvalidUserInputException("Session ID is required for refresh tokens")
        
        # Rule 3: Check token rotation rules
        if token_type == TokenType.REFRESH and previous_token_jti:
            await self._validate_token_rotation(previous_token_jti)
        
        # Rule 4: Check blacklist for previous tokens (if applicable)
        if previous_token_jti and await self._is_token_blacklisted(previous_token_jti):
            raise InvalidUserInputException("Previous token has been revoked")

    async def _build_token_claims(self,
                                user_id: str,
                                email: str,
                                token_type: TokenType,
                                roles: List[str],
                                permissions: List[str],
                                session_id: str,
                                purpose: str) -> Dict[str, Any]:
        """Build token claims according to business rules and token type"""
        
        base_claims = {
            'sub': user_id,
            'email': email,
            'token_type': token_type.value,
            'jti': str(uuid.uuid4()),  # Unique token identifier
            'iat': datetime.utcnow(),
        }
        
        # Add type-specific claims
        if token_type == TokenType.ACCESS:
            base_claims.update({
                'roles': roles or [],
                'permissions': permissions or [],
                'session_id': session_id
            })
        elif token_type == TokenType.REFRESH:
            base_claims.update({
                'session_id': session_id,
                'rotation_count': await self._get_rotation_count(session_id)
            })
        elif token_type in [TokenType.RESET_PASSWORD, TokenType.EMAIL_VERIFICATION]:
            base_claims.update({
                'purpose': purpose,
                'single_use': True
            })
        
        # Filter claims based on allowed claims for token type
        policy = self.token_policies.get(token_type, {})
        allowed_claims = policy.get('allowed_claims', [])
        return {k: v for k, v in base_claims.items() if k in allowed_claims}

    async def _generate_token_by_type(self, token_type: TokenType, claims: Dict[str, Any]) -> str:
        """Generate token based on type with appropriate expiration"""
        
        policy = self.token_policies.get(token_type, {})
        expiry = policy.get('expiry', timedelta(hours=1))
        
        if token_type == TokenType.ACCESS:
            return self.jwt_manager.create_access_token(**claims)
        elif token_type == TokenType.REFRESH:
            return self.jwt_manager.create_refresh_token(**claims)
        elif token_type == TokenType.RESET_PASSWORD:
            return self.jwt_manager.create_token(
                claims, 
                expires_delta=expiry,
                token_type=token_type
            )
        elif token_type == TokenType.EMAIL_VERIFICATION:
            return self.jwt_manager.create_token(
                claims,
                expires_delta=expiry,
                token_type=token_type
            )
        else:
            raise InvalidUserInputException(f"Unsupported token type: {token_type}")

    async def _validate_token_rotation(self, previous_token_jti: str):
        """Enforce token rotation rules to prevent token reuse"""
        
        # Rule: Check if previous token was recently used
        last_rotation = await self._get_last_rotation_time(previous_token_jti)
        if last_rotation and datetime.utcnow() - last_rotation < timedelta(seconds=30):
            raise InvalidUserInputException("Token rotation too frequent")
        
        # Rule: Check rotation count limit
        rotation_count = await self._get_rotation_count_by_jti(previous_token_jti)
        if rotation_count >= 5:  # Maximum 5 rotations per session
            raise InvalidUserInputException("Maximum token rotations exceeded")

    async def _apply_post_generation_rules(self, 
                                         token_type: TokenType,
                                         token_metadata: Dict[str, Any],
                                         previous_token_jti: str):
        """Apply business rules after token generation"""
        
        # Rule: For refresh token rotation, revoke previous token
        if token_type == TokenType.REFRESH and previous_token_jti:
            await self._revoke_previous_token(previous_token_jti)
        
        # Rule: Track token generation for audit purposes
        await self._track_token_generation(token_metadata, token_type)
        
        # Rule: For single-use tokens, mark as used immediately in storage
        policy = self.token_policies.get(token_type, {})
        if policy.get('single_use'):
            await self._mark_token_as_used(token_metadata['jti'])

    def _extract_token_metadata(self, token: str, token_type: TokenType) -> Dict[str, Any]:
        """Extract metadata from generated token for tracking"""
        
        try:
            payload = self.jwt_manager.get_token_metadata(token)
            return {
                'jti': payload.get('jti'),
                'user_id': payload.get('sub'),
                'email': payload.get('email'),
                'token_type': token_type,
                'session_id': payload.get('session_id'),
                'issued_at': payload.get('iat'),
                'expires_at': payload.get('exp'),
                'roles': payload.get('roles', []),
                'permissions': payload.get('permissions', [])
            }
        except Exception as e:
            logger.error(f"Failed to extract token metadata: {str(e)}")
            return {}

    def _format_token_response(self, 
                             token: str, 
                             metadata: Dict[str, Any],
                             token_type: TokenType) -> Dict[str, Any]:
        """Format token response according to business requirements"""
        
        response = {
            "token": token,
            "token_type": "bearer",
            "jti": metadata.get('jti'),
            "user_id": metadata.get('user_id'),
            "session_id": metadata.get('session_id'),
            "issued_at": metadata.get('issued_at'),
            "expires_at": metadata.get('expires_at')
        }
        
        # Add type-specific response fields
        if token_type == TokenType.ACCESS:
            response.update({
                "roles": metadata.get('roles', []),
                "permissions": metadata.get('permissions', [])
            })
        elif token_type == TokenType.REFRESH:
            response["rotation_count"] = metadata.get('rotation_count', 0)
        
        return response

    # Business Rule Implementation Methods
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted (implement based on your storage)"""
        # Implementation depends on your blacklist storage (Redis, DB, etc.)
        return False  # Placeholder

    async def _get_rotation_count(self, session_id: str) -> int:
        """Get current rotation count for session"""
        # Implementation depends on your storage
        return 0  # Placeholder

    async def _get_last_rotation_time(self, jti: str) -> Optional[datetime]:
        """Get last rotation time for token"""
        # Implementation depends on your storage
        return None  # Placeholder

    async def _get_rotation_count_by_jti(self, jti: str) -> int:
        """Get rotation count by token JTI"""
        # Implementation depends on your storage
        return 0  # Placeholder

    async def _revoke_previous_token(self, jti: str):
        """Revoke previous token during rotation"""
        # Implementation: Add to blacklist or mark as revoked in storage
        logger.info(f"Revoking previous token: {jti}")

    async def _track_token_generation(self, metadata: Dict[str, Any], token_type: TokenType):
        """Track token generation for audit and security"""
        # Implementation: Log to audit trail or security monitoring system
        logger.info(f"Token generated - Type: {token_type}, User: {metadata.get('user_id')}, JTI: {metadata.get('jti')}")

    async def _mark_token_as_used(self, jti: str):
        """Mark single-use token as used"""
        # Implementation: Store in used tokens table or similar
        logger.info(f"Marking token as used: {jti}")