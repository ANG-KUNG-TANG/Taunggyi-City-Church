from functools import wraps
from registry import get_schema
from exceptons import ValdationError


def validate(schema_name: str):
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            schema = get_schema(schema_name)
            raw_data = kwargs.get('data') or {}
            try:
                validated_data = schema(**raw_data)
            except Exception as e:
                raise ValdationError(str(e))
            kwargs['validated_data'] = validated_data
            return func(*args, **kwargs)
        return wrapper
    return decorator