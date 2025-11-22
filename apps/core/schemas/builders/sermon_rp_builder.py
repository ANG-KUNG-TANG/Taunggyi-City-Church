from typing import Any, Dict, List
from apps.core.schemas.schemas.sermons import SermonResponseSchema, SermonListResponseSchema
from apps.tcc.usecase.entities.sermons import SermonEntity  # Assuming you have a SermonEntity

class SermonResponseBuilder:
    """
    Centralized builder for creating sermon response schemas.
    Works like a serializer but stays framework-independent.
    Automatically maps entity attributes to SermonResponseSchema fields.
    """

    @staticmethod
    def to_response(entity: Any) -> SermonResponseSchema:
        """
        Convert a sermon entity → SermonResponseSchema automatically.

        It dynamically collects all fields defined in the schema.
        """
        # Extract all fields defined in SermonResponseSchema
        schema_fields = SermonResponseSchema.model_fields.keys()

        data: Dict[str, Any] = {}
        for field in schema_fields:
            # Safely retrieve value from entity, fallback to None
            data[field] = getattr(entity, field, None)

        # Return fully validated Pydantic schema
        return SermonResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> SermonListResponseSchema:
        """
        Convert a list of sermon entities to a paginated list response.
        """
        sermon_responses = [SermonResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return SermonListResponseSchema(
            sermons=sermon_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @staticmethod
    def to_public_response(entity: Any) -> Dict[str, Any]:
        """
        Convert sermon entity to public response format (excludes sensitive data).
        """
        sermon_response = SermonResponseBuilder.to_response(entity)
        
        # Remove any sensitive fields for public responses
        public_data = sermon_response.model_dump()
        
        # Example: Remove internal fields if needed
        # public_data.pop('internal_notes', None)
        
        return public_data

    @staticmethod
    def to_minimal_response(entity: Any) -> Dict[str, Any]:
        """
        Convert sermon entity to minimal response format (for lists, previews).
        """
        minimal_fields = ['id', 'title', 'preacher', 'bible_passage', 'sermon_date', 'thumbnail_url']
        
        data = {}
        for field in minimal_fields:
            data[field] = getattr(entity, field, None)
        
        return data