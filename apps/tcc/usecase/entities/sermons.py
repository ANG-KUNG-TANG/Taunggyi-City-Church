from schemas.sermons import SermonCreateSchema
import html


class SermonEntity(SermonCreateSchema):
    """Sermon entity with security and business logic"""
    
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
    
    def validate_business_rules(self):
        """Sermon-specific business rules"""
        if self.duration_minutes and self.duration_minutes > 480:  # 8 hours max
            raise ValueError("Sermon duration too long")
        
        # Validate bible passage format
        if self.bible_passage and not self.is_valid_bible_reference(self.bible_passage):
            raise ValueError("Invalid bible reference format")
    
    @staticmethod
    def is_valid_bible_reference(reference: str) -> bool:
        """Basic bible reference validation"""
        import re
        pattern = r'^[1-9]?[A-Za-z]+\s+\d+:\d+'
        return bool(re.match(pattern, reference))
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        self.validate_business_rules()