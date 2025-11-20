from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository, PrayerResponseRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity, PrayerResponseEntity
from apps.tcc.models.base.enums import PrayerPrivacy, PrayerCategory, PrayerStatus
from usecase.domain_exception.p_exceptions import (
    PrayerException,
    PrayerRequestNotFoundException,
    PrayerCategoryInvalidException
)


class CreatePrayerUseCase(BaseUseCase):
    """Use case for creating new prayer requests"""
    
    def __init__(self):
        super().__init__()
        self.prayer_repository = PrayerRepository() 
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        required_fields = ['title', 'content']
        missing_fields = [field for field in required_fields if not input_data.get(field)]
        
        if missing_fields:
            raise PrayerException(
                message="Missing required fields",
                error_code="MISSING_REQUIRED_FIELDS",
                details={"missing_fields": missing_fields},
                user_message="Please provide all required fields: title and content."
            )
        
        # Validate category if provided
        category = input_data.get('category')
        if category:
            self._validate_category(category)

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        # Create PrayerRequestEntity
        prayer_entity = PrayerRequestEntity(
            title=input_data['title'],
            content=input_data['content'],
            category=input_data.get('category', PrayerCategory.GENERAL),
            privacy=input_data.get('privacy', PrayerPrivacy.PUBLIC),
            status=input_data.get('status', PrayerStatus.ACTIVE),
            is_answered=False,
            answer_notes=input_data.get('answer_notes', ''),
            user_id=user.id
        )
        
        # Create prayer request using repository
        created_prayer = await self.prayer_repository.create(prayer_entity)
        
        return {
            "message": "Prayer request created successfully",
            "prayer": self._format_prayer_response(created_prayer)
        }

    def _validate_category(self, category: str) -> None:
        """Validate prayer category"""
        allowed_categories = [choice.value for choice in PrayerCategory]
        
        if category not in allowed_categories:
            raise PrayerCategoryInvalidException(
                category=category,
                allowed_categories=allowed_categories,
                user_message=f"Category '{category}' is not supported. Please choose from: {', '.join(allowed_categories)}"
            )

    @staticmethod
    def _format_prayer_response(prayer_entity: PrayerRequestEntity) -> Dict[str, Any]:
        """Format prayer entity for response"""
        return {
            'id': prayer_entity.id,
            'user_id': prayer_entity.user_id,
            'title': prayer_entity.title,
            'content': prayer_entity.content,
            'category': prayer_entity.category.value if hasattr(prayer_entity.category, 'value') else prayer_entity.category,
            'privacy': prayer_entity.privacy.value if hasattr(prayer_entity.privacy, 'value') else prayer_entity.privacy,
            'status': prayer_entity.status.value if hasattr(prayer_entity.status, 'value') else prayer_entity.status,
            'is_answered': prayer_entity.is_answered,
            'answer_notes': prayer_entity.answer_notes,
            'is_active': prayer_entity.is_active,
            'created_at': prayer_entity.created_at,
            'updated_at': prayer_entity.updated_at,
            'expires_at': prayer_entity.expires_at
        }


class CreatePrayerResponseUseCase(BaseUseCase):
    """Use case for creating prayer responses"""
    
    def __init__(self):
        super().__init__()
        self.prayer_response_repository = PrayerResponseRepository()  
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        prayer_id = input_data.get('prayer_id')
        content = input_data.get('content')
        
        if not prayer_id:
            raise PrayerException(
                message="Prayer ID is required",
                error_code="MISSING_PRAYER_ID",
                user_message="Prayer request ID is required."
            )
        
        if not content:
            raise PrayerException(
                message="Response content is required",
                error_code="MISSING_RESPONSE_CONTENT",
                user_message="Please provide response content."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        prayer_id = input_data['prayer_id']
        content = input_data['content']
        is_private = input_data.get('is_private', False)
        
        # Create PrayerResponseEntity
        response_entity = PrayerResponseEntity(
            prayer_request_id=prayer_id,
            user_id=user.id,
            content=content,
            is_private=is_private
        )
        
        # Create response using repository
        created_response = await self.prayer_response_repository.create(response_entity)
        
        return {
            "message": "Prayer response created successfully",
            "response": self._format_response_response(created_response)
        }

    @staticmethod
    def _format_response_response(response_entity: PrayerResponseEntity) -> Dict[str, Any]:
        """Format prayer response entity for response"""
        return {
            'id': response_entity.id,
            'prayer_request_id': response_entity.prayer_request_id,
            'user_id': response_entity.user_id,
            'content': response_entity.content,
            'is_private': response_entity.is_private,
            'is_active': response_entity.is_active,
            'created_at': response_entity.created_at,
            'updated_at': response_entity.updated_at
        }