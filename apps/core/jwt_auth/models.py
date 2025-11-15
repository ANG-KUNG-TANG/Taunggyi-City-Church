from django.db import models
from django.conf import settings

class RefreshToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'jwt_refresh_tokens'