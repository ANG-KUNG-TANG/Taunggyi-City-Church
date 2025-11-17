from typing import Dict, Any, List, Optional
from usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.entities.prayer import PrayerRequestEntity, PrayerResponseEntity
from apps.tcc.models.base.enums import PrayerCategory
from usecase.domain_exception.p_exceptions import (
    PrayerException,
    PrayerRequestNotFoundException,
    PrayerCategoryInvalidException
)


class GetPrayerRequestByIdUseCase(BaseUseCase):
    """Use case for getting prayer request by ID"""
    
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
        prayer_entity = await self.prayer_request_repository.get_by_id(prayer_id, user)
        
        if not prayer_entity:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        return {
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


class GetAllPrayerRequestsUseCase(BaseUseCase):
    """Use case for getting all prayer requests with optional filtering"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        prayers = await self.prayer_request_repository.get_all(user, filters)
        
        return {
            "prayers": [self._format_prayer_response(prayer) for prayer in prayers],
            "total_count": len(prayers)
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


class GetPublicPrayerRequestsUseCase(BaseUseCase):
    """Use case for getting public prayer requests"""
    
    def _setup_configuration(self):
        self.config.require_authentication = False  # Public prayers can be viewed without auth

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        limit = input_data.get('limit')
        prayers = await self.prayer_request_repository.get_public_prayers(user, limit)
        
        return {
            "prayers": [self._format_prayer_response(prayer) for prayer in prayers],
            "total_count": len(prayers)
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


class GetUserPrayerRequestsUseCase(BaseUseCase):
    """Use case for getting all prayer requests by a user"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        prayers = await self.prayer_request_repository.get_user_prayers(user)
        
        return {
            "prayers": [self._format_prayer_response(prayer) for prayer in prayers],
            "total_count": len(prayers)
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


class GetPrayerRequestsByCategoryUseCase(BaseUseCase):
    """Use case for getting prayers by category"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        category = input_data.get('category')
        if not category:
            raise PrayerException(
                message="Category is required",
                error_code="MISSING_CATEGORY",
                user_message="Prayer category is required."
            )
        
        self._validate_category(category)

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        category = input_data['category']
        prayers = await self.prayer_request_repository.get_prayers_by_category(category, user)
        
        return {
            "prayers": [self._format_prayer_response(prayer) for prayer in prayers],
            "category": category.value if hasattr(category, 'value') else category,
            "total_count": len(prayers)
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


class GetPrayerResponseByIdUseCase(BaseUseCase):
    """Use case for getting prayer response by ID"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _validate_input(self, input_data: Dict[str, Any], context):
        response_id = input_data.get('response_id')
        if not response_id:
            raise PrayerException(
                message="Response ID is required",
                error_code="MISSING_RESPONSE_ID",
                user_message="Prayer response ID is required."
            )

    async def _on_execute(self, input_data: Dict[str, Any], user, context) -> Dict[str, Any]:
        response_id = input_data['response_id']
        response_entity = await self.prayer_response_repository.get_by_id(response_id, user)
        
        if not response_entity:
            raise PrayerException(
                message=f"Prayer response {response_id} not found",
                error_code="PRAYER_RESPONSE_NOT_FOUND",
                user_message="Prayer response not found."
            )
        
        return {
            "response": self._format_response_response(response_entity)
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


class GetPrayerResponsesForPrayerUseCase(BaseUseCase):
    """Use case for getting all responses for a prayer request"""
    
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
        
        # Verify prayer exists and user can access it
        prayer_entity = await self.prayer_request_repository.get_by_id(prayer_id, user)
        if not prayer_entity:
            raise PrayerRequestNotFoundException(
                prayer_id=str(prayer_id),
                user_message="Prayer request not found."
            )
        
        responses = await self.prayer_response_repository.get_responses_for_prayer(prayer_id, user)
        
        return {
            "prayer_id": prayer_id,
            "responses": [self._format_response_response(response) for response in responses],
            "total_count": len(responses)
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