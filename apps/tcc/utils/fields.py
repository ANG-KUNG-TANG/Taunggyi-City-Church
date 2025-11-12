from django.db import models
from .snowflake import generate_snowflake_id

class SnowflakeField(models.BigIntegerField):
    """
    Custom field for Snowflake IDs
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        kwargs['default'] = generate_snowflake_id
        kwargs['editable'] = False
        super().__init__(*args, **kwargs)
    
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Don't include default in migrations
        if 'default' in kwargs:
            del kwargs['default']
        return name, path, args, kwargs