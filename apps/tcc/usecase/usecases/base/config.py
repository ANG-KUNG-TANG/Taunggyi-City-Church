from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


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


class AuthorizationManager:
    """Handles use case authorization"""
    
    @staticmethod
    def is_authorized(user, config: UseCaseConfiguration) -> bool:
        """Check if user is authorized for the operation"""
        # Skip auth if not required
        if not config.require_authentication:
            return True

        # Basic user checks
        if not user or not getattr(user, 'is_active', True):
            return False

        # Role-based authorization
        if config.required_roles and getattr(user, 'role', None) not in config.required_roles:
            return False

        # Permission-based authorization
        if config.required_permissions:
            user_permissions = getattr(user, 'get_permissions', lambda: {})()
            return all(user_permissions.get(perm, False) for perm in config.required_permissions)

        return True