from typing import Any, Dict, List
from datetime import datetime
from apps.core.schemas.schemas.prayer import PrayerRequestResponseSchema, PrayerRequestListResponseSchema
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity
from apps.core.schemas.common.response import APIResponse

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
            # Map entity fields to schema fields
            value = getattr(entity, field, None)
            
            # Handle special cases
            if field == 'is_expired':
                if hasattr(entity, 'expires_at') and entity.expires_at:
                    value = entity.expires_at < datetime.now()
                else:
                    value = False
            
            data[field] = value
        
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
        Convert prayer request entity to public response format.
        """
        prayer_response = PrayerResponseBuilder.to_response(entity)
        public_data = prayer_response.model_dump()
        
        # Remove user identification for privacy
        public_data.pop('user_id', None)
        
        return public_data

    @staticmethod
    def to_anonymous_response(entity: Any) -> Dict[str, Any]:
        """
        Convert prayer request entity to anonymous format (for public prayer walls).
        """
        prayer_response = PrayerResponseBuilder.to_response(entity)
        anonymous_data = prayer_response.model_dump()
        
        # Keep only minimal public fields
        allowed_fields = ['id', 'title', 'content', 'privacy', 'prayer_count', 'created_at', 'is_expired']
        return {field: anonymous_data[field] for field in allowed_fields if field in anonymous_data}