# # [file name]: user_repository.py
# from typing import Dict, Any, Optional
# from django.db.models import Q

# from base_repository import BaseRepository
# from users import User
# from schemas import (
#     UserCreateSchema, 
#     UserUpdateSchema, 
#     UserResponseSchema,
#     UserQuerySchema
# )
# from exceptions import ValidationError


# class UserRepository(BaseRepository[User, UserCreateSchema, UserUpdateSchema, UserResponseSchema]):
#     """
#     User repository extending BaseRepository with user-specific operations
#     """
    
#     def __init__(self):
#         super().__init__(User)
    
#     def _to_response_schema(self, user: User) -> UserResponseSchema:
#         """Convert User model instance to UserResponseSchema"""
#         return UserResponseSchema(
#             id=user.id,
#             username=user.email,  # Using email as username based on your model
#             email=user.email,
#             phone=getattr(user, 'phone', None),
#             full_name=user.name,
#             is_active=user.is_active if hasattr(user, 'is_active') else True,
#             created_at=user.created_at if hasattr(user, 'created_at') else None,
#             updated_at=user.updated_at if hasattr(user, 'updated_at') else None
#         )
    
#     def _build_query_filters(self, query_params: UserQuerySchema) -> Q:
#         """Build Django Q objects for user query filtering"""
#         filters = Q()
        
#         if hasattr(query_params, 'search') and query_params.search:
#             search_filter = (
#                 Q(name__icontains=query_params.search) |
#                 Q(email__icontains=query_params.search)
#             )
#             filters &= search_filter
        
#         if hasattr(query_params, 'is_active') and query_params.is_active is not None:
#             filters &= Q(is_active=query_params.is_active)
        
#         if hasattr(query_params, 'membership_status') and query_params.membership_status:
#             filters &= Q(membership_status=query_params.membership_status)
        
#         return filters
    
#     def create(self, create_data: UserCreateSchema, **kwargs) -> UserResponseSchema:
#         """
#         Create a new user with proper password handling
#         """
#         try:
#             # Check if user already exists
#             if self.exists(email=create_data.email):
#                 raise EntityAlreadyExistsError(f"User with email {create_data.email} already exists")
            
#             # Create user instance
#             user = User(
#                 name=create_data.full_name or create_data.username,
#                 email=create_data.email,
#             )
            
#             # Set password properly
#             user.set_password(create_data.password)
            
#             # Set additional fields
#             if hasattr(user, 'phone') and create_data.phone:
#                 user.phone = create_data.phone
            
#             user.save()
            
#             return self._to_response_schema(user)
            
#         except EntityAlreadyExistsError:
#             raise
#         except Exception as e:
#             raise RepositoryError(f"Failed to create user: {str(e)}")
    
#     def update(self, user_id: int, update_data: UserUpdateSchema) -> UserResponseSchema:
#         """
#         Update user with proper email uniqueness check and password handling
#         """
#         try:
#             user = self.model.objects.get(id=user_id)
            
#             # Convert update data to dictionary, excluding unset fields
#             update_dict = update_data.dict(exclude_unset=True)
            
#             # Update fields if provided
#             if 'full_name' in update_dict and update_dict['full_name']:
#                 user.name = update_dict['full_name']
            
#             if 'email' in update_dict and update_dict['email']:
#                 # Check if email is not already taken by another user
#                 if self.model.objects.filter(email=update_dict['email']).exclude(id=user_id).exists():
#                     raise ValidationError(f"Email {update_dict['email']} is already taken")
#                 user.email = update_dict['email']
            
#             if 'password' in update_dict and update_dict['password']:
#                 user.set_password(update_dict['password'])
            
#             if 'phone' in update_dict and hasattr(user, 'phone'):
#                 user.phone = update_dict['phone']
            
#             user.save()
            
#             return self._to_response_schema(user)
            
#         except ObjectDoesNotExist:
#             raise EntityNotFoundError(f"User with ID {user_id} not found")
#         except ValidationError:
#             raise
#         except Exception as e:
#             raise RepositoryError(f"Failed to update user: {str(e)}")
    
#     def get_user_by_email(self, email: str) -> UserResponseSchema:
#         """
#         Get user by email address
#         """
#         return self.get_by_field('email', email)
    
#     def list_users(self, query_params: UserQuerySchema) -> Dict[str, Any]:
#         """
#         List users with user-specific pagination
#         """
#         return self.list_paginated(
#             query_params=query_params,
#             page=getattr(query_params, 'page', 1),
#             page_size=getattr(query_params, 'page_size', 20),
#             sort_by=getattr(query_params, 'sort_by', 'id'),
#             sort_order=getattr(query_params, 'sort_order', 'asc')
#         )


# # Factory function for dependency injection
# def get_user_repository() -> UserRepository:
#     """Factory function to get UserRepository instance"""
#     return UserRepository()


# __all__ = ['UserRepository', 'get_user_repository']