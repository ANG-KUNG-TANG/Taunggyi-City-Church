import bcrypt
import secrets
import string
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class PasswordService:
    """Service for password hashing and verification"""
    
    async def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}")
            raise ValueError("Failed to hash password")
    
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            if not plain_password or not hashed_password:
                return False
            
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            return False
    
    def is_password_strong(self, password: str) -> Tuple[bool, Optional[str]]:
        """Check password strength"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, ", ".join(errors) if errors else None
    
    async def generate_temporary_password(self) -> str:
        """Generate a secure temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        return temp_password
    
    async def password_needs_rehash(self, hashed_password: str) -> bool:
        """Check if password needs rehashing (e.g., after algorithm updates)"""
        try:
            # bcrypt automatically handles this, but we can add custom logic
            # For now, just return False as bcrypt handles it
            return False
        except:
            return False