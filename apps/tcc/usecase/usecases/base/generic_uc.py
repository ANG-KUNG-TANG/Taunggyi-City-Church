from typing import TypeVar, Generic, Dict, Any, List
from apps.core.core_exceptions.domain import DomainException
from apps.core.schemas.out_schemas.base import DeleteResponseSchema
from .base_uc import BaseUseCase

T = TypeVar('T')  # Entity type
S = TypeVar('S')  # Response schema type

class GenericCRUDUseCase(BaseUseCase, Generic[T, S]):
    """Generic CRUD operations that work for ANY entity"""
    
    def __init__(self, repository, response_schema: type, **dependencies):
        super().__init__(repository=repository, **dependencies)
        self.repository = repository
        self.response_schema = response_schema

    async def _convert_to_response(self, entity: T) -> S:
        """Convert entity to response schema"""
        return self.response_schema.model_validate(entity)

    def _get_entity_name(self) -> str:
        """Get entity name from class name"""
        class_name = self.__class__.__name__
        if class_name.endswith('UseCase'):
            class_name = class_name[:-7]
        # Remove CRUD operation prefixes
        for prefix in ['Get', 'Create', 'Update', 'Delete', 'List', 'Search']:
            if class_name.startswith(prefix):
                class_name = class_name[len(prefix):]
        return class_name or "Entity"


class GenericGetByIdUseCase(GenericCRUDUseCase[T, S]):
    """Generic get by ID for ANY entity"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data, user, ctx) -> S:
        entity_id = await self._validate_entity_id(
            input_data.get('id') or input_data.get(f'{self._get_entity_name().lower()}_id'),
            f"{self._get_entity_name()} ID"
        )
        
        entity = await self.repository.get_by_id(entity_id)
        if not entity:
            raise DomainException(
                message=f"{self._get_entity_name()} not found",
                error_code="NOT_FOUND",
                status_code=404
            )
        
        return await self._convert_to_response(entity)


class GenericCreateUseCase(GenericCRUDUseCase[T, S]):
    """Generic create for ANY entity"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data, user, ctx) -> S:
        entity_data = self._add_audit_context(input_data, user, ctx)
        created_entity = await self.repository.create(entity_data)
        return await self._convert_to_response(created_entity)


class GenericUpdateUseCase(GenericCRUDUseCase[T, S]):
    """Generic update for ANY entity"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data, user, ctx) -> S:
        entity_id = await self._validate_entity_id(
            input_data.get('id') or input_data.get(f'{self._get_entity_name().lower()}_id'),
            f"{self._get_entity_name()} ID"
        )
        
        update_data = self._add_audit_context(
            input_data.get('update_data', {}), 
            user, 
            ctx
        )
        
        updated_entity = await self.repository.update(entity_id, update_data)
        if not updated_entity:
            raise DomainException(
                message=f"Failed to update {self._get_entity_name().lower()}",
                error_code="UPDATE_FAILED",
                status_code=400
            )
        
        return await self._convert_to_response(updated_entity)


class GenericDeleteUseCase(GenericCRUDUseCase[T, S]):
    """Generic delete for ANY entity"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data, user, ctx) -> DeleteResponseSchema:
        entity_id = await self._validate_entity_id(
            input_data.get('id') or input_data.get(f'{self._get_entity_name().lower()}_id'),
            f"{self._get_entity_name()} ID"
        )
        
        success = await self.repository.delete(entity_id)
        if not success:
            raise DomainException(
                message=f"Failed to delete {self._get_entity_name().lower()}",
                error_code="DELETE_FAILED",
                status_code=400
            )
        
        return DeleteResponseSchema(
            id=entity_id,
            deleted=success,
            message=f"{self._get_entity_name()} deleted successfully"
        )


class GenericListUseCase(GenericCRUDUseCase[T, S]):
    """Generic list with pagination for ANY entity"""
    
    def _setup_configuration(self):
        self.config.require_authentication = True

    async def _on_execute(self, input_data, user, ctx) -> Dict[str, Any]:
        filters = input_data.get('filters', {})
        page = input_data.get('page', 1)
        per_page = input_data.get('per_page', 20)
        
        # Use repository's paginated method
        entities, total_count = await self.repository.get_paginated(
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        # Convert to response schemas
        items = [await self._convert_to_response(entity) for entity in entities]
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        
        return {
            "items": items,
            "total": total_count,
            "page": page,
            "page_size": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }