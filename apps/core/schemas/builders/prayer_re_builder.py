from typing import Any, Dict, List
from datetime import datetime
from apps.core.schemas.schemas.prayer import PrayerRequestResponseSchema, PrayerRequestListResponseSchema
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity  # Assuming you have this entity

class PrayerResponseBuilder:
    """
    Centralized builder for creating prayer request response schemas.
    """

    @staticmethod
    def to_response(entity: Any) -> PrayerRequestResponseSchema:
        """
        Convert a prayer request entity → PrayerRequestResponseSchema automatically.
        """
        schema_fields = PrayerRequestResponseSchema.model_fields.keys()
        
        data: Dict[str, Any] = {}
        for field in schema_fields:
            data[field] = getattr(entity, field, None)
        
        # Calculate is_expired based on expires_at
        if hasattr(entity, 'expires_at') and entity.expires_at:
            data['is_expired'] = entity.expires_at < datetime.now()
        else:
            data['is_expired'] = False
        
        return PrayerRequestResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> PrayerRequestListResponseSchema:
        """
        Convert a list of prayer request entities to a paginated list response.
        """
        prayer_responses = [PrayerResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return PrayerRequestListResponseSchema(
            prayer_requests=prayer_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @staticmethod
    def to_public_response(entity: Any) -> Dict[str, Any]:
        """
        Convert prayer request entity to public response format (based on privacy).
        """
        prayer_response = PrayerResponseBuilder.to_response(entity)
        
        public_data = prayer_response.model_dump()
        
        # Remove sensitive information based on privacy settings
        if hasattr(entity, 'privacy'):
            if entity.privacy.value == 'PRIVATE':  # Adjust based on your enum values
                # Remove user identification for private prayers
                public_data.pop('user_id', None)
                public_data.pop('user_name', None)
        
        return public_data

    @staticmethod
    def to_anonymous_response(entity: Any) -> Dict[str, Any]:
        """
        Convert prayer request entity to anonymous format (for public prayer walls).
        """
        anonymous_fields = ['id', 'title', 'content', 'privacy', 'prayer_count', 'created_at']
        
        data = {}
        for field in anonymous_fields:
            data[field] = getattr(entity, field, None)
        
        return data