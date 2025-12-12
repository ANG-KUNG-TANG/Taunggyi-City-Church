from typing import Dict, Any
import logging
from apps.core.jwt.jwt_backend import JWTBackend

logger = logging.getLogger(__name__)

class RegisterUseCase:
    """User registration use case"""
    
    def __init__(self, user_repository, password_hasher, jwt_backend: JWTBackend):
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.jwt_backend = jwt_backend
    
    async def execute(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Execute user registration"""
        try:
            # Check if user already exists
            existing_user = await self.user_repository.get_by_email(email)
            if existing_user:
                raise ValueError("User with this email already exists")
            
            # Hash password
            hashed_password = self.password_hasher.hash_password(password)
            
            # Create user
            user = await self.user_repository.create_user(
                email=email,
                password_hash=hashed_password,
                full_name=full_name,
                is_active=True
            )
            
            # Assign default role
            await self.user_repository.assign_default_role(user.id)
            
            # Get user roles
            roles = await self.user_repository.get_user_roles(user.id)
            role_names = [role.name for role in roles] if roles else ["user"]
            
            # Create JWT tokens
            tokens = await self.jwt_backend.create_tokens(
                user_id=str(user.id),
                email=user.email,
                roles=role_names
            )
            
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": tokens["token_type"],
                "expires_in": tokens["expires_in"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": role_names
                }
            }
            
        except ValueError as e:
            logger.warning(f"Registration failed for {email}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            raise RuntimeError("Registration failed due to system error")
