from typing import Any, Dict, List
from apps.core.schemas.schemas.users import UserResponseSchema, UserListResponseSchema
from apps.tcc.usecase.entities.users import UserEntity

class UserResponseBuilder:
    """
    Centralized builder for creating user response schemas.
    Works like a serializer but stays framework-independent.
    Automatically maps entity attributes to UserResponseSchema fields.
    """

    @staticmethod
    def to_response(entity: Any) -> UserResponseSchema:
        """
        Convert a user entity → UserResponseSchema automatically.

        It dynamically collects all fields defined in the schema.
        """
        # Extract all fields defined in UserResponseSchema
        schema_fields = UserResponseSchema.model_fields.keys()

        data: Dict[str, Any] = {}
        for field in schema_fields:
            # Safely retrieve value from entity, fallback to None
            data[field] = getattr(entity, field, None)

        # Return fully validated Pydantic schema
        return UserResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[UserEntity], total: int = None, 
                        page: int = 1, per_page: int = 20) -> UserListResponseSchema:
        """
        Convert a list of user entities to a paginated list response.
        """
        user_responses = [UserResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return UserListResponseSchema(
            users=user_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @staticmethod
    def to_auth_response(entity: UserEntity, access_token: str, 
                        refresh_token: str = None) -> Dict[str, Any]:
        """
        Convert user entity to authentication response format.
        """
        from apps.core.schemas.schemas.users import UserAuthResponseSchema
        
        user_response = UserResponseBuilder.to_response(entity)
        
        return UserAuthResponseSchema(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token or access_token
        ).model_dump()