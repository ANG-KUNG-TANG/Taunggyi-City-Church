from asyncio import Event
from datetime import timezone
from models.base.base import BaseModel
from models.base.enums import SermonStatus
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
    
    sermon_date = models.DateTimeField(default=timezone.now)
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
    
    # Link to event if this was part of a service
    event = models.ForeignKey(
        Event, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sermons'
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


# class SermonMedia(BaseModel):
#     sermon = models.ForeignKey(
#         Sermon,
#         on_delete=models.CASCADE,
#         related_name='media_files'
#     )
#     media_type = models.CharField(
#         max_length=20,
#         choices=MediaType.choices,
#         default=MediaType.AUDIO
#     )
#     file = models.FileField(
#         upload_to='sermons/',
#         help_text="Media file (audio/video)"
#     )
#     url = models.URLField(
#         blank=True,
#         help_text="External media URL"
#     )
#     duration = models.PositiveIntegerField(
#         null=True,
#         blank=True,
#         help_text="Media duration in seconds"
#     )
#     file_size = models.PositiveIntegerField(
#         null=True,
#         blank=True,
#         help_text="File size in bytes"
#     )
    
#     class Meta:
#         db_table = "sermon_media"
#         verbose_name = "Sermon Media"
#         verbose_name_plural = "Sermon Media"
    
#     def __str__(self):
#         return f"{self.get_media_type_display()} for {self.sermon.title}"

