# from asyncio import exceptions
# from asyncio.log import logger
# from django.contrib.auth import get_user_model
# from rest_framework.authentication import BaseAuthentication

# from apps.core.jwt_auth.security import jwt_manager
# from apps.core.jwt_auth.security.jwt_manager import TokenExpiredError, TokenInvalidError, TokenRevokedError

# def get_authorization_header(request):
#     raise NotImplementedError

# class JWTAuthentication(BaseAuthentication):
#     keyword = "Bearer"

#     def authenticate(self, request):
#         auth = get_authorization_header(request).split()
        
#         if not auth or auth[0].decode().lower() != self.keyword.lower():
#             return None
            
#         if len(auth) == 1:
#             raise exceptions.AuthenticationFailed("Invalid token header. No credentials provided.")
#         if len(auth) > 2:
#             raise exceptions.AuthenticationFailed("Invalid token header. Token string should not contain spaces.")

#         try:
#             token = auth[1].decode()
#         except UnicodeError:
#             raise exceptions.AuthenticationFailed("Invalid token header. Token string should not contain invalid characters.")

#         try:
#             payload = jwt_manager.validate_access_token(token)
#         except TokenExpiredError:
#             raise exceptions.AuthenticationFailed("Token has expired.")
#         except TokenRevokedError:
#             raise exceptions.AuthenticationFailed("Token has been revoked.")
#         except TokenInvalidError as e:
#             raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}")
#         except Exception as e:
#             logger.error(f"Unexpected error during token validation: {e}")
#             raise exceptions.AuthenticationFailed("Authentication service unavailable.")

#         user_id = payload.get("sub")
#         if not user_id:
#             raise exceptions.AuthenticationFailed("Token missing subject (sub).")

#         try:
#             # Use Django's user model instead of hardcoded repository
#             User = get_user_model()
#             user = User.objects.get(id=int(user_id))
            
#             # Check if user is active
#             if not user.is_active:
#                 raise exceptions.AuthenticationFailed("User account is disabled.")
                
#         except User.DoesNotExist:
#             raise exceptions.AuthenticationFailed("User not found.")
#         except ValueError:
#             raise exceptions.AuthenticationFailed("Invalid user ID in token.")

#         return (user, token)