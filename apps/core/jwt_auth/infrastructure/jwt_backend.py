# from datetime import timedelta
# from django.conf import settings

# from apps.core.jwt_auth.security.blacklist_service import RedisBlacklistService
# from apps.core.jwt_auth.security.jwt_manager import JWTConfig, JWTManager


# _blacklist = RedisBlacklistService()

# cfg = JWTConfig(
#     secret=settings.JWT["SECRET"],
#     algorithm=settings.JWT["ALGORITHM"],
#     issuer=settings.JWT.get("ISSUER"),
#     audience=settings.JWT.get("AUDIENCE"),
#     access_lifetime=settings.JWT["ACCESS_LIFETIME"],
#     refresh_lifetime=settings.JWT["REFRESH_LIFETIME"],
# )

# jwt_manager = JWTManager(cfg, is_revoked=_blacklist.is_revoked, revoke_callback=_blacklist.revoke)
