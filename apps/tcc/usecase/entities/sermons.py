# import re
# from typing import Optional
# from apps.core.schemas.input_schemas.sermons import SermonCreateSchema
# from apps.tcc.models.base.enums import SermonStatus
# from .base_entity import BaseEntity


# class SermonEntity(BaseEntity):
#     def __init__(self, sermon_data: SermonCreateSchema = None, **kwargs):
#         super().__init__(**kwargs)
        
#         if sermon_data:
#             self.title = sermon_data.title
#             self.preacher = sermon_data.preacher
#             self.bible_passage = sermon_data.bible_passage
#             self.description = sermon_data.description
#             self.content = sermon_data.content
#             self.duration_minutes = sermon_data.duration_minutes
#             self.sermon_date = sermon_data.sermon_date
#             self.video_url = getattr(sermon_data, 'video_url', None)
#             self.audio_url = getattr(sermon_data, 'audio_url', None)
#             self.thumbnail_url = getattr(sermon_data, 'thumbnail_url', None)
#             self.status = getattr(sermon_data, 'status', SermonStatus.DRAFT)
#         else:
#             # For repository conversion
#             self.title = kwargs.get('title')
#             self.preacher = kwargs.get('preacher')
#             self.bible_passage = kwargs.get('bible_passage')
#             self.description = kwargs.get('description')
#             self.content = kwargs.get('content')
#             self.duration_minutes = kwargs.get('duration_minutes')
#             self.sermon_date = kwargs.get('sermon_date')
#             self.audio_url = kwargs.get('audio_url')
#             self.video_url = kwargs.get('video_url')
#             self.thumbnail_url = kwargs.get('thumbnail_url')
#             self.status = kwargs.get('status', SermonStatus.DRAFT)
#             self.view_count = kwargs.get('view_count', 0)
#             self.like_count = kwargs.get('like_count', 0)
    
#     def sanitize_inputs(self):
#         """Sanitize sermon content"""
#         self.title = self.sanitize_string(self.title)
#         self.preacher = self.sanitize_string(self.preacher)
#         self.bible_passage = self.sanitize_string(self.bible_passage)
#         self.description = self.sanitize_string(self.description)
#         self.content = self.sanitize_string(self.content)
    
#     def prepare_for_persistence(self):
#         """Prepare entity for database operations"""
#         self.sanitize_inputs()
#         self.update_timestamps()
    
#     @classmethod
#     def from_model(cls, model):
#         """Create entity from Django model"""
#         return cls(
#             id=model.id,
#             title=model.title,
#             preacher=model.preacher,
#             bible_passage=model.bible_passage,
#             description=model.description,
#             content=model.content,
#             duration_minutes=model.duration_minutes,
#             sermon_date=model.sermon_date,
#             audio_url=model.audio_url,
#             video_url=model.video_url,
#             thumbnail_url=model.thumbnail_url,
#             status=model.status,
#             view_count=model.view_count,
#             like_count=model.like_count,
#             created_at=model.created_at,
#             updated_at=model.updated_at
#         )
    
#     @staticmethod
#     def is_valid_bible_reference(reference: str) -> bool:
#         """Basic bible reference validation"""
#         if not reference:
#             return False
#         pattern = r'^[1-9]?[A-Za-z]+\s+\d+:\d+'
#         return bool(re.match(pattern, reference))
    
#     def __str__(self):
#         return f"SermonEntity(id={self.id}, title='{self.title}', preacher='{self.preacher}')"