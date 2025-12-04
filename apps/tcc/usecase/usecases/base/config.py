from typing import List, Optional, Any, Dict, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger("app.usecase")

# ============ AUTHORIZATION ENUMS ============

class Permission(Enum):
    """System-wide permissions"""
    CAN_MANAGE_USERS = "can_manage_users"
    CAN_VIEW_USERS = "can_view_users"
    CAN_DELETE_USERS = "can_delete_users"
    CAN_UPDATE_USERS = "can_update_users"
    CAN_CREATE_USERS = "can_create_users"
    CAN_MANAGE_ROLES = "can_manage_roles"
    CAN_VIEW_AUDIT_LOGS = "can_view_audit_logs"

class Role(Enum):
    """System roles with hierarchy"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"

# Role hierarchy (higher roles inherit lower role permissions)
ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: [Role.ADMIN, Role.MANAGER, Role.USER, Role.GUEST],
    Role.ADMIN: [Role.MANAGER, Role.USER, Role.GUEST],
    Role.MANAGER: [Role.USER, Role.GUEST],
    Role.USER: [Role.GUEST],
    Role.GUEST: []
}

# Role to permission mapping
ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: {
        Permission.CAN_MANAGE_USERS,
        Permission.CAN_VIEW_USERS,
        Permission.CAN_DELETE_USERS,
        Permission.CAN_UPDATE_USERS,
        Permission.CAN_CREATE_USERS,
        Permission.CAN_MANAGE_ROLES,
        Permission.CAN_VIEW_AUDIT_LOGS,
    },
    Role.ADMIN: {
        Permission.CAN_MANAGE_USERS,
        Permission.CAN_VIEW_USERS,
        Permission.CAN_DELETE_USERS,
        Permission.CAN_UPDATE_USERS,
        Permission.CAN_CREATE_USERS,
        Permission.CAN_VIEW_AUDIT_LOGS,
    },
    Role.MANAGER: {
        Permission.CAN_VIEW_USERS,
        Permission.CAN_UPDATE_USERS,
        Permission.CAN_CREATE_USERS,
    },
    Role.USER: {
        Permission.CAN_VIEW_USERS,
    },
    Role.GUEST: set()
}

# ============ CONFIGURATION CLASSES ============

@dataclass
class UseCaseConfiguration:
    """Configuration for use case execution"""
    require_authentication: bool = True
    required_roles: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    transactional: bool = True
    validate_input: bool = True
    validate_output: bool = True
    audit_log: bool = True

@dataclass
class OperationContext:
    """Execution context for use case operations"""
    operation_id: str
    user: Optional[Any]
    input_data: Any
    output_data: Any = None
    error: Optional[Exception] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============ AUTHORIZATION MANAGER ============

class AuthorizationManager:
    """Enhanced authorization with role hierarchy and resource-level checks"""
    
    def __init__(self):
        self._permission_cache = {}
    
    async def is_authorized(self, user: Any, config: UseCaseConfiguration, resource: Any = None) -> bool:
        """
        Comprehensive authorization check
        
        Args:
            user: The user to authorize
            config: Use case configuration with requirements
            resource: Optional resource for context-aware authorization
            
        Returns:
            bool: True if authorized
        """
        # Skip auth if not required
        if not config.require_authentication:
            return True

        # Basic user validation
        if not await self._is_valid_user(user):
            return False

        # Check role-based authorization
        if not await self._has_required_roles(user, config.required_roles):
            return False

        # Check permission-based authorization
        if not await self._has_required_permissions(user, config.required_permissions, resource):
            return False

        return True
    
    async def _is_valid_user(self, user: Any) -> bool:
        """Validate user is active and authenticated"""
        if not user:
            return False
        
        # Check user is active
        if not getattr(user, 'is_active', True):
            logger.warning(f"Authorization failed: user {getattr(user, 'id', 'unknown')} is inactive")
            return False
        
        # Check user is authenticated
        if not getattr(user, 'is_authenticated', True):
            logger.warning(f"Authorization failed: user {getattr(user, 'id', 'unknown')} is not authenticated")
            return False
            
        return True
    
    async def _has_required_roles(self, user: Any, required_roles: List[str]) -> bool:
        """Check if user has required roles considering hierarchy"""
        if not required_roles:
            return True
        
        user_role = getattr(user, 'role', None)
        if not user_role:
            return False
        
        try:
            user_role_enum = Role(user_role)
        except ValueError:
            logger.warning(f"Unknown user role: {user_role}")
            return False
        
        # Check if user's role or any higher role matches required roles
        user_effective_roles = [user_role_enum] + ROLE_HIERARCHY.get(user_role_enum, [])
        user_role_names = {role.value for role in user_effective_roles}
        
        has_role = any(required_role in user_role_names for required_role in required_roles)
        
        if not has_role:
            logger.warning(
                f"Role authorization failed: user has {user_role}, required {required_roles}"
            )
        
        return has_role
    
    async def _has_required_permissions(self, user: Any, required_permissions: List[str], resource: Any) -> bool:
        """Check if user has required permissions"""
        if not required_permissions:
            return True
        
        user_permissions = await self._get_user_permissions(user)
        
        # Check each required permission
        for perm_name in required_permissions:
            try:
                permission = Permission(perm_name)
                if permission not in user_permissions:
                    logger.warning(f"Missing permission: {perm_name}")
                    return False
                    
                # Resource-level authorization if resource provided
                if resource and not await self._check_resource_permission(user, permission, resource):
                    logger.warning(f"Resource permission denied: {perm_name} for resource {resource}")
                    return False
                    
            except ValueError:
                logger.warning(f"Unknown permission: {perm_name}")
                return False
        
        return True
    
    async def _get_user_permissions(self, user: Any) -> Set[Permission]:
        """Get user's effective permissions considering role hierarchy"""
        cache_key = f"user_{getattr(user, 'id', 'anonymous')}_permissions"
        
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        user_role = getattr(user, 'role', None)
        if not user_role:
            return set()
        
        try:
            user_role_enum = Role(user_role)
        except ValueError:
            return set()
        
        # Get permissions from role hierarchy
        effective_permissions = set()
        user_effective_roles = [user_role_enum] + ROLE_HIERARCHY.get(user_role_enum, [])
        
        for role in user_effective_roles:
            effective_permissions.update(ROLE_PERMISSIONS.get(role, set()))
        
        # Add any explicit user permissions
        explicit_permissions = getattr(user, 'get_permissions', lambda: set())()
        for perm_name in explicit_permissions:
            try:
                effective_permissions.add(Permission(perm_name))
            except ValueError:
                continue
        
        self._permission_cache[cache_key] = effective_permissions
        return effective_permissions
    
    async def _check_resource_permission(self, user: Any, permission: Permission, resource: Any) -> bool:
        """
        Resource-level authorization check.
        Override in subclasses for specific resource types.
        """
        # Example: Check if user owns the resource
        if hasattr(resource, 'user_id') and hasattr(user, 'id'):
            return resource.user_id == user.id
        
        # Example: Check department/team access
        if hasattr(resource, 'department_id') and hasattr(user, 'department_id'):
            return resource.department_id == user.department_id
        
        # Default: allow if user has the general permission
        return True
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear permission cache"""
        if user_id:
            cache_key = f"user_{user_id}_permissions"
            self._permission_cache.pop(cache_key, None)
        else:
            self._permission_cache.clear()