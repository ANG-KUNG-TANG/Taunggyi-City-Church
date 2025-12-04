import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, Generic, List
from django.db import transaction
from asgiref.sync import sync_to_async

from apps.core.core_exceptions.domain import DomainException
from apps.core.schemas.out_schemas.base import DeleteResponseSchema
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    AuthorizationException, 
    UnauthenticatedException
)
from .config import UseCaseConfiguration, OperationContext, AuthorizationManager

logger = logging.getLogger("app.usecase")

T = TypeVar('T')  # Entity type
S = TypeVar('S')  # Response schema type

class BaseUseCase:
    """
    Base UseCase for ALL entities (User, Event, Prayer, etc.)
    """

    def __init__(self, **dependencies):
        self.config = UseCaseConfiguration()
        self.authorization_manager = dependencies.get('authorization_manager', AuthorizationManager())
        self._setup_configuration()
        
        # Inject ALL dependencies dynamically
        for key, value in dependencies.items():
            setattr(self, key, value)

    def _setup_configuration(self):
        """Override in subclasses to configure use case behavior"""
        pass

    async def execute(self, input_data, user=None, context=None):
        """Main execution entry point"""
        operation_ctx = OperationContext(
            operation_id=str(uuid.uuid4()),
            user=user,
            input_data=input_data,
            metadata={'context': context} if context else {}
        )

        try:
            await self._before_execute(operation_ctx)
            result = await self._execute_main_logic(operation_ctx)
            operation_ctx.output_data = result
            await self._after_execute(operation_ctx)
            return result

        except DomainException:
            raise
        except Exception as exc:
            operation_ctx.error = exc
            raise await self._handle_exception(exc, operation_ctx)
        finally:
            await self._finalize_execution(operation_ctx)

    async def _before_execute(self, ctx: OperationContext):
        """Pre-execution: auth, authorization, validation"""
        if self.config.require_authentication and not ctx.user:
            raise UnauthenticatedException("Authentication required")

        authorized = await self.authorization_manager.is_authorized(ctx.user, self.config)
        if not authorized:
            raise AuthorizationException("Insufficient permissions")

        if self.config.validate_input:
            await self._validate_input(ctx.input_data, ctx)

    async def _execute_main_logic(self, ctx: OperationContext):
        """Execute with transaction support"""
        if self.config.transactional:
            async with transaction.async_atomic():
                return await self._on_execute(ctx.input_data, ctx.user, ctx)
        else:
            return await self._on_execute(ctx.input_data, ctx.user, ctx)

    async def _after_execute(self, ctx: OperationContext):
        """Post-execution: output validation"""
        if self.config.validate_output:
            await self._validate_output(ctx.output_data, ctx)

    async def _finalize_execution(self, ctx: OperationContext):
        """Always executes: logging, cleanup"""
        ctx.end_time = datetime.utcnow()
        duration = (ctx.end_time - ctx.start_time).total_seconds()
        
        if self.config.audit_log:
            await self._log_operation(ctx, duration)

    async def _log_operation(self, ctx: OperationContext, duration: float):
        """Generic logging"""
        log_data = {
            "operation": self.__class__.__name__,
            "operation_id": ctx.operation_id,
            "user_id": getattr(ctx.user, 'id', 'anonymous'),
            "duration_seconds": round(duration, 3),
            "success": ctx.error is None
        }
        
        if ctx.error:
            logger.warning(f"UseCase failed: {log_data}")
        else:
            logger.info(f"UseCase executed: {log_data}")

    async def _handle_exception(self, exc: Exception, ctx: OperationContext) -> DomainException:
        """Generic exception handling"""
        logger.error(
            f"Unexpected error in {self.__class__.__name__}: {exc}",
            exc_info=True,
            extra={"operation_id": ctx.operation_id}
        )
        
        return DomainException(
            message="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            status_code=500
        )

    # Utility methods for ALL entities
    async def _validate_entity_id(self, entity_id: Any, id_name: str = "ID") -> int:
        """Generic ID validation for ANY entity"""
        if not entity_id:
            raise DomainException(
                message=f"{id_name} is required",
                error_code="MISSING_ID",
                status_code=400
            )
        
        try:
            return int(entity_id)
        except (ValueError, TypeError):
            raise DomainException(
                message=f"{id_name} must be a valid number",
                error_code="INVALID_ID",
                status_code=400
            )

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _add_audit_context(self, data: Dict[str, Any], user, context) -> Dict[str, Any]:
        """Add audit context to data"""
        data_with_context = data.copy()
        data_with_context['user'] = user
        
        if context and hasattr(context, 'request'):
            request = context.request
            data_with_context['ip_address'] = self._get_client_ip(request)
            data_with_context['user_agent'] = request.META.get('HTTP_USER_AGENT', 'system')
        
        return data_with_context

    # Template methods - override in concrete use cases
    async def _validate_input(self, input_data, ctx: OperationContext):
        pass

    async def _validate_output(self, output_data, ctx: OperationContext):
        pass

    async def _on_execute(self, input_data, user, ctx: OperationContext):
        raise NotImplementedError(f"{self.__class__.__name__} must implement _on_execute()")

# ============ GENERIC CRUD USE CASES ============

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