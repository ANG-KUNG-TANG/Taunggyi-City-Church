from django.db import models
from django.db.models import Q


class ChurchInformation(models.Model):
    """
    Stores the single public-information record for Taunggyi City Church.
    """

    id = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )
    church_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    service_times = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tcc"
        db_table = "church_information"
        constraints = [
            models.CheckConstraint(
                condition=Q(id=1),
                name="church_information_single_record",
            ),
        ]

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.church_name
