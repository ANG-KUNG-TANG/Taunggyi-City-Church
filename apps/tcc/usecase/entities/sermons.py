import html
import re
from datetime import datetime
from apps.core.schemas.schemas.sermons import SermonCreateSchema
from apps.tcc.models.base.enums import SermonStatus


class SermonEntity:
    def __init__(self, sermon_data: SermonCreateSchema = None, **kwargs):
        if sermon_data:
            self.title = sermon_data.title
            self.preacher = sermon_data.preacher
            self.bible_passage = sermon_data.bible_passage
            self.description = sermon_data.description
            self.content = sermon_data.content
            self.duration_minutes = sermon_data.duration_minutes
            self.sermon_date = sermon_data.sermon_date
            self.video_url = getattr(sermon_data, 'video_url', None)
            self.audio_url = getattr(sermon_data, 'audio_url', None)
            self.thumbnail_url = getattr(sermon_data, 'thumbnail_url', None)
            self.status = getattr(sermon_data, 'status', SermonStatus.DRAFT)
        else:
            # For repository conversion
            self.id = kwargs.get('id')
            self.title = kwargs.get('title')
            self.preacher = kwargs.get('preacher')
            self.bible_passage = kwargs.get('bible_passage')
            self.description = kwargs.get('description')
            self.content = kwargs.get('content')
            self.duration_minutes = kwargs.get('duration_minutes')
            self.sermon_date = kwargs.get('sermon_date')
            self.audio_url = kwargs.get('audio_url')
            self.video_url = kwargs.get('video_url')
            self.thumbnail_url = kwargs.get('thumbnail_url')
            self.status = kwargs.get('status', SermonStatus.DRAFT)
            self.view_count = kwargs.get('view_count', 0)
            self.like_count = kwargs.get('like_count', 0)
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    def sanitize_inputs(self):
        """Sanitize sermon content"""
        if hasattr(self, 'title'):
            self.title = html.escape(self.title.strip())
        if hasattr(self, 'preacher'):
            self.preacher = html.escape(self.preacher.strip())
        if hasattr(self, 'bible_passage') and self.bible_passage:
            self.bible_passage = html.escape(self.bible_passage.strip())
        if hasattr(self, 'description') and self.description:
            self.description = html.escape(self.description.strip())
        if hasattr(self, 'content') and self.content:
            self.content = html.escape(self.content.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
    
    @staticmethod
    def is_valid_bible_reference(reference: str) -> bool:
        """Basic bible reference validation"""
        if not reference:
            return False
        pattern = r'^[1-9]?[A-Za-z]+\s+\d+:\d+'
        return bool(re.match(pattern, reference))
    
    def __str__(self):
        return f"{self.title} by {self.preacher}"