# [file name]: base_repository.py
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from django.db import models, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet

from helpers.validators.exceptions import (
    EntityNotFoundError, 
    EntityAlreadyExistsError,
    RepositoryError
)

# Type variables for generic repository
TModel = TypeVar('TModel', bound=models.Model)
TCreateSchema = TypeVar('TCreateSchema')
TUpdateSchema = TypeVar('TUpdateSchema')
TResponseSchema = TypeVar('TResponseSchema')


class BaseRepository(Generic[TModel, TCreateSchema, TUpdateSchema, TResponseSchema]):
    """
    Base repository providing common CRUD operations for all entities
    """
    
    def __init__(self, model: Type[TModel]):
        self.model = model
    
    def _to_response_schema(self, instance: TModel) -> TResponseSchema:
        """
        Convert model instance to response schema.
        Must be implemented by child classes.
        """
        raise NotImplementedError("Child classes must implement _to_response_schema")
    
    def _build_query_filters(self, query_params: Any) -> Q:
        """
        Build Django Q objects for query filtering.
        Can be overridden by child classes for entity-specific filtering.
        
        Args:
            query_params: Query parameters object
            
        Returns:
            Q object with filters
        """
        return Q()
    
    def _apply_ordering(self, queryset: QuerySet, sort_by: str, sort_order: str) -> QuerySet:
        """
        Apply ordering to queryset
        
        Args:
            queryset: Django queryset
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Ordered queryset
        """
        if sort_order == 'desc':
            sort_field = f'-{sort_by}'
        else:
            sort_field = sort_by
        
        # Validate that the sort field exists on the model
        if hasattr(self.model, sort_by):
            return queryset.order_by(sort_field)
        
        return queryset
    
    def _apply_pagination(self, queryset: QuerySet, page: int, page_size: int) -> QuerySet:
        """
        Apply pagination to queryset
        
        Args:
            queryset: Django queryset
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Paginated queryset
        """
        offset = (page - 1) * page_size
        return queryset[offset:offset + page_size]
    
    @transaction.atomic
    def create(self, create_data: TCreateSchema, **kwargs) -> TResponseSchema:
        """
        Create a new entity
        
        Args:
            create_data: Validated creation data
            **kwargs: Additional parameters for entity creation
            
        Returns:
            TResponseSchema: Created entity data
            
        Raises:
            EntityAlreadyExistsError: If entity with unique constraints already exists
            RepositoryError: For database operation errors
        """
        try:
            # Convert schema to model creation dictionary
            create_dict = create_data.dict() if hasattr(create_data, 'dict') else dict(create_data)
            
            # Merge with additional kwargs
            create_dict.update(kwargs)
            
            # Create instance
            instance = self.model.objects.create(**create_dict)
            
            return self._to_response_schema(instance)
            
        except Exception as e:
            # Handle unique constraint violations
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                raise EntityAlreadyExistsError(f"{self.model.__name__} already exists: {str(e)}")
            raise RepositoryError(f"Failed to create {self.model.__name__}: {str(e)}")
    
    def get_by_id(self, entity_id: int) -> TResponseSchema:
        """
        Get entity by ID
        
        Args:
            entity_id: Entity ID
            
        Returns:
            TResponseSchema: Entity data
            
        Raises:
            EntityNotFoundError: If entity not found
            RepositoryError: For database operation errors
        """
        try:
            instance = self.model.objects.get(id=entity_id)
            return self._to_response_schema(instance)
        except ObjectDoesNotExist:
            raise EntityNotFoundError(f"{self.model.__name__} with ID {entity_id} not found")
        except Exception as e:
            raise RepositoryError(f"Failed to get {self.model.__name__} by ID: {str(e)}")
    
    def get_by_field(self, field: str, value: Any) -> TResponseSchema:
        """
        Get entity by specific field value
        
        Args:
            field: Field name to search by
            value: Field value to match
            
        Returns:
            TResponseSchema: Entity data
            
        Raises:
            EntityNotFoundError: If entity not found
            RepositoryError: For database operation errors
        """
        try:
            filter_kwargs = {field: value}
            instance = self.model.objects.get(**filter_kwargs)
            return self._to_response_schema(instance)
        except ObjectDoesNotExist:
            raise EntityNotFoundError(f"{self.model.__name__} with {field} '{value}' not found")
        except Exception as e:
            raise RepositoryError(f"Failed to get {self.model.__name__} by {field}: {str(e)}")
    
    def list_all(
        self, 
        query_params: Any = None,
        sort_by: str = "id",
        sort_order: str = "asc"
    ) -> List[TResponseSchema]:
        """
        List all entities with optional filtering and sorting
        
        Args:
            query_params: Query parameters for filtering
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            List of entity data
        """
        try:
            # Build filters
            filters = self._build_query_filters(query_params) if query_params else Q()
            
            # Get queryset and apply ordering
            queryset = self.model.objects.filter(filters)
            queryset = self._apply_ordering(queryset, sort_by, sort_order)
            
            instances = list(queryset)
            return [self._to_response_schema(instance) for instance in instances]
            
        except Exception as e:
            raise RepositoryError(f"Failed to list {self.model.__name__}: {str(e)}")
    
    def list_paginated(
        self, 
        query_params: Any,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "id", 
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        List entities with pagination
        
        Args:
            query_params: Query parameters for filtering
            page: Page number (1-indexed)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Dict containing entities list and pagination metadata
        """
        try:
            # Build filters
            filters = self._build_query_filters(query_params) if query_params else Q()
            
            # Get queryset
            queryset = self.model.objects.filter(filters)
            
            # Apply ordering
            queryset = self._apply_ordering(queryset, sort_by, sort_order)
            
            # Get total count before pagination
            total_count = queryset.count()
            
            # Apply pagination
            paginated_queryset = self._apply_pagination(queryset, page, page_size)
            instances = list(paginated_queryset)
            
            # Convert to response schemas
            entities = [self._to_response_schema(instance) for instance in instances]
            
            return {
                'data': entities,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': (total_count + page_size - 1) // page_size,
                    'has_next': (page * page_size) < total_count,
                    'has_previous': page > 1
                }
            }
            
        except Exception as e:
            raise RepositoryError(f"Failed to list paginated {self.model.__name__}: {str(e)}")
    
    @transaction.atomic
    def update(self, entity_id: int, update_data: TUpdateSchema) -> TResponseSchema:
        """
        Update entity data
        
        Args:
            entity_id: Entity ID to update
            update_data: Validated update data
            
        Returns:
            TResponseSchema: Updated entity data
            
        Raises:
            EntityNotFoundError: If entity not found
            RepositoryError: For database operation errors
        """
        try:
            instance = self.model.objects.get(id=entity_id)
            
            # Convert update data to dictionary, excluding unset fields
            update_dict = update_data.dict(exclude_unset=True) if hasattr(update_data, 'dict') else dict(update_data)
            
            # Update instance fields
            for field, value in update_dict.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
            
            instance.save()
            
            return self._to_response_schema(instance)
            
        except ObjectDoesNotExist:
            raise EntityNotFoundError(f"{self.model.__name__} with ID {entity_id} not found")
        except Exception as e:
            raise RepositoryError(f"Failed to update {self.model.__name__}: {str(e)}")
    
    @transaction.atomic
    def delete(self, entity_id: int, soft_delete: bool = True) -> bool:
        """
        Delete entity by ID
        
        Args:
            entity_id: Entity ID to delete
            soft_delete: Whether to perform soft delete if available
            
        Returns:
            bool: True if successful
            
        Raises:
            EntityNotFoundError: If entity not found
            RepositoryError: For database operation errors
        """
        try:
            instance = self.model.objects.get(id=entity_id)
            
            # Try soft delete first if requested and available
            if soft_delete and hasattr(instance, 'is_active'):
                instance.is_active = False
                instance.save()
            elif soft_delete and hasattr(instance, 'deleted_at'):
                from django.utils import timezone
                instance.deleted_at = timezone.now()
                instance.save()
            else:
                # Hard delete
                instance.delete()
                
            return True
            
        except ObjectDoesNotExist:
            raise EntityNotFoundError(f"{self.model.__name__} with ID {entity_id} not found")
        except Exception as e:
            raise RepositoryError(f"Failed to delete {self.model.__name__}: {str(e)}")
    
    def exists(self, **filters) -> bool:
        """
        Check if entity exists with given filters
        
        Args:
            **filters: Filter conditions
            
        Returns:
            bool: True if entity exists
        """
        try:
            return self.model.objects.filter(**filters).exists()
        except Exception as e:
            raise RepositoryError(f"Failed to check {self.model.__name__} existence: {str(e)}")
    
    def count(self, **filters) -> int:
        """
        Count entities matching given filters
        
        Args:
            **filters: Filter conditions
            
        Returns:
            int: Count of matching entities
        """
        try:
            return self.model.objects.filter(**filters).count()
        except Exception as e:
            raise RepositoryError(f"Failed to count {self.model.__name__}: {str(e)}")


# Update exceptions to include base entity errors