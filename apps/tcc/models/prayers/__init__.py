from apps.tcc.models.base.base import BaseModel, User
from django.db import models

class PrayerRequest(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prayer_requests')
    content = models.TextField()
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return f"Prayer request by {self.user.name}"

    class Meta:
        verbose_name = 'Prayer Request'
        verbose_name_plural = 'Prayer Requests'