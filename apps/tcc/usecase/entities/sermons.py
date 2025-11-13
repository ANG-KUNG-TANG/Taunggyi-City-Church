import html
import re

from apps.core.schemas.sermons import SermonCreateSchema

class SermonEntity:
    def __init__(self, sermon_data: SermonCreateSchema):
        self.title = sermon_data.title
        self.preacher = sermon_data.preacher
        self.bible_passage = sermon_data.bible_passage
        self.description = sermon_data.description
        self.content = sermon_data.content
        self.duration_minutes = sermon_data.duration_minutes
        self.sermon_date = sermon_data.sermon_date
    
    def sanitize_inputs(self):
        """Sanitize sermon content"""
        self.title = html.escape(self.title.strip())
        self.preacher = html.escape(self.preacher.strip())
        if self.bible_passage:
            self.bible_passage = html.escape(self.bible_passage.strip())
        if self.description:
            self.description = html.escape(self.description.strip())
        if self.content:
            self.content = html.escape(self.content.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
    @staticmethod
    def is_valid_bible_reference(reference: str) -> bool:
        """Basic bible reference validation"""
        pattern = r'^[1-9]?[A-Za-z]+\s+\d+:\d+'
        return bool(re.match(pattern, reference))