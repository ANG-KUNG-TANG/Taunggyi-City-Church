from datetime import datetime
from apps.tcc.models.base.base_model import BaseModel
from apps.tcc.models.base.enums import SermonStatus
from django.db import models


class Sermon(BaseModel):
    title = models.CharField(max_length=200, help_text="Sermon title")
    preacher = models.CharField(max_length=120, help_text="Name of preacher/pastor")
    bible_passage = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Bible reference (e.g., John 3:16)"
    )
    description = models.TextField(blank=True, help_text="Sermon summary")
    content = models.TextField(blank=True, help_text="Full sermon content/notes")
    
    sermon_date = models.DateTimeField(default=datetime.now) 
    status = models.CharField(
        max_length=20,
        choices=SermonStatus.choices,
        default=SermonStatus.DRAFT
    )
    
    duration_minutes = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Sermon duration in minutes"
    )
    
    
    class Meta:
        db_table = "sermons"
        verbose_name = "Sermon"
        verbose_name_plural = "Sermons"
        ordering = ['-sermon_date']
        indexes = [
            models.Index(fields=['sermon_date']),
            models.Index(fields=['preacher']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.preacher}"