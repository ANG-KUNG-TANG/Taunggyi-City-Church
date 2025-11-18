# import bcrypt
# import secrets
# from typing import Tuple
# import logging

# logger = logging.getLogger(__name__)

# class PasswordHasher:
#     @staticmethod
#     def hash_password(password: str) -> Tuple[str, str]:
#         """Hash password with random salt"""
#         try:
#             # Generate salt and hash
#             salt = bcrypt.gensalt(rounds=12)
#             hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
#             return hashed.decode('utf-8'), salt.decode('utf-8')
#         except Exception as e:
#             logger.error(f"Password hashing failed: {e}")
#             raise

#     @staticmethod
#     def verify_password(password: str, hashed_password: str) -> bool:
#         """Verify password against hash"""
#         try:
#             return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
#         except Exception as e:
#             logger.error(f"Password verification failed: {e}")
#             return False

#     @staticmethod
#     def generate_secure_token(length: int = 32) -> str:
#         """Generate cryptographically secure token"""
#         return secrets.token_urlsafe(length)