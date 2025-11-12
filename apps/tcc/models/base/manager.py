from django.db import models
from apps.tcc.utils.snowflake import generate_snowflake_id

class BaseModelManager(models.Manager):
    """
    Custom manager for BaseModel with Snowflake ID support
    """
    
    def get_queryset(self):
        """Return only active objects by default"""
        return super().get_queryset().filter(is_active=True)
    
    def all_with_inactive(self):
        """Return all objects including inactive ones"""
        return super().get_queryset()
    
    def inactive(self):
        """Return only inactive objects"""
        return super().get_queryset().filter(is_active=False)
    
    def create_with_id(self, **kwargs):
        """
        Create object with explicit Snowflake ID
        """
        if 'id' not in kwargs:
            kwargs['id'] = generate_snowflake_id()
        return self.create(**kwargs)
    
    def bulk_create_with_ids(self, objs, batch_size=None):
        """
        Bulk create objects with Snowflake IDs
        """
        for obj in objs:
            if not obj.id:
                obj.id = generate_snowflake_id()
        return super().bulk_create(objs, batch_size=batch_size)
    
    def get_by_snowflake(self, snowflake_id):
        """
        Get object by Snowflake ID
        """
        return self.get_queryset().get(id=snowflake_id)
    
    def filter_by_snowflake_range(self, start_id, end_id):
        """
        Filter objects by Snowflake ID range
        Useful for time-based queries
        """
        return self.get_queryset().filter(id__range=(start_id, end_id))