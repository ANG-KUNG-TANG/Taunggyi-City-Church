from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository, PrayerResponseRepository
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity, PrayerResponseEntity
from apps.tcc.models.base.enums import PrayerCategory
from usecase.domain_exception.p_exceptions import (
    PrayerException,
    PrayerRequestNotFoundException,
    PrayerRequestAlreadyAnsweredException,
    PrayerResponseNotAllowedException,
    PrayerCategoryInvalidException
)


class UpdatePrayerRequestUseCase(BaseUseCase):
    """Use case for updating prayer requests"""
    
    def __init__(self):
        super().__init__()
        self.prayer_repository = PrayerRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        prayer_id = input_data.get('prayer_id')
        if not prayer_id:
            raise PrayerException(
                message="Prayer ID is required",
                error_code="MISSING_PRAYER_ID",
                user_message="Prayer request ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        prayer_id = input_data['prayer_id']
        
        # Check if prayer exists and user has permission
        existing_prayer = await self.prayer_repository.get_by_id(prayer_id)
        if not existing_prayer:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        # Check if user owns the prayer
        if existing_prayer.user_id != user.id:
            raise PrayerResponseNotAllowedException(
                prayer_id=str(prayer_id),
                user_id=str(user.id),
                reason="User is not the owner of this prayer request",
                user_message="You can only update your own prayer requests."
            )
        
        # Check if prayer is already answered
        if existing_prayer.is_answered:
            raise PrayerRequestAlreadyAnsweredException(
                prayer_id=str(prayer_id),
                answered_at=str(existing_prayer.updated_at),
                user_message="Cannot update an answered prayer request."
            )
        
        # Validate category if being updated
        if 'category' in input_data:
            self._validate_category(input_data['category'])
        
        # Create updated PrayerRequestEntity
        updated_prayer_entity = PrayerRequestEntity(
            id=prayer_id,
            user_id=existing_prayer.user_id,
            title=input_data.get('title', existing_prayer.title),
            content=input_data.get('content', existing_prayer.content),
            category=input_data.get('category', existing_prayer.category),
            privacy=input_data.get('privacy', existing_prayer.privacy),
            status=input_data.get('status', existing_prayer.status),
            is_answered=existing_prayer.is_answered,
            answer_notes=existing_prayer.answer_notes,
            is_active=existing_prayer.is_active,
            created_at=existing_prayer.created_at,
            updated_at=existing_prayer.updated_at,
            expires_at=existing_prayer.expires_at
        )
        
        # Update prayer request using repository
        updated_prayer = await self.prayer_repository.update(prayer_id, updated_prayer_entity)
        
        if not updated_prayer:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found for update."
            )
        
        return {
            "message": "Prayer request updated successfully",
            "prayer": self._format_prayer_response(updated_prayer)
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


class UpdatePrayerResponseUseCase(BaseUseCase):
    """Use case for updating prayer responses"""
    
    def __init__(self):
        super().__init__()
        self.prayer_response_repository = PrayerResponseRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        response_id = input_data.get('response_id')
        content = input_data.get('content')
        
        if not response_id:
            raise PrayerException(
                message="Response ID is required",
                error_code="MISSING_RESPONSE_ID",
                user_message="Prayer response ID is required."
            )
        
        if not content:
            raise PrayerException(
                message="Response content is required",
                error_code="MISSING_RESPONSE_CONTENT",
                user_message="Please provide response content."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        response_id = input_data['response_id']
        content = input_data['content']
        
        # Get existing response to verify ownership
        existing_response = await self.prayer_response_repository.get_by_id(response_id)
        if not existing_response:
            raise PrayerException(
                message=f"Prayer response {response_id} not found",
                error_code="PRAYER_RESPONSE_NOT_FOUND",
                user_message="Prayer response not found."
            )
        
        # Only allow the response owner to update
        if existing_response.user_id != user.id:
            raise PrayerResponseNotAllowedException(
                prayer_id=str(existing_response.prayer_request_id),
                user_id=str(user.id),
                reason="User is not the owner of this response",
                user_message="You can only update your own prayer responses."
            )
        
        # Create updated PrayerResponseEntity
        updated_response_entity = PrayerResponseEntity(
            id=response_id,
            prayer_request_id=existing_response.prayer_request_id,
            user_id=existing_response.user_id,
            content=content,
            is_private=existing_response.is_private,
            is_active=existing_response.is_active,
            created_at=existing_response.created_at,
            updated_at=existing_response.updated_at
        )
        
        # Update response using repository
        updated_response = await self.prayer_response_repository.update(response_id, updated_response_entity)
        
        if not updated_response:
            raise PrayerException(
                message=f"Prayer response {response_id} not found for update",
                error_code="PRAYER_RESPONSE_UPDATE_FAILED",
                user_message="Prayer response not found for update."
            )
        
        return {
            "message": "Prayer response updated successfully",
            "response": self._format_response_response(updated_response)
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


class MarkPrayerRequestAnsweredUseCase(BaseUseCase):
    """Use case for marking prayer requests as answered"""
    
    def __init__(self):
        super().__init__()
        self.prayer_repository = PrayerRepository()  # Instantiate directly
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        prayer_id = input_data.get('prayer_id')
        if not prayer_id:
            raise PrayerException(
                message="Prayer ID is required",
                error_code="MISSING_PRAYER_ID",
                user_message="Prayer request ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        prayer_id = input_data['prayer_id']
        answer_notes = input_data.get('answer_notes', '')
        
        # Mark prayer as answered using repository
        prayer_entity = await self.prayer_repository.mark_as_answered(prayer_id, user.id, answer_notes)
        
        if not prayer_entity:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        return {
            "message": "Prayer request marked as answered successfully",
            "prayer": self._format_prayer_response(prayer_entity)
        }

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