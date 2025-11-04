from django.db import models
from apps.tcc.utils.snowflake import generate_snowflake_id

class SnowflakeField(models.BigIntegerField):
    """
    Custom model field for Snowflake IDs.
    Automatically generates Snowflake IDs for primary keys.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        kwargs['editable'] = False
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)
    
    def pre_save(self, model_instance, add):
        """
        Generate Snowflake ID before saving if it doesn't exist.
        """
        if add and not getattr(model_instance, self.attname):
            value = generate_snowflake_id()
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)
    
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Remove the arguments we set in __init__
        kwargs.pop('primary_key', None)
        kwargs.pop('editable', None)
        kwargs.pop('unique', None)
        return name, path, args, kwargs