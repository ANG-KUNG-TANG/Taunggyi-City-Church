from enum import Enum
from typing import Set, Optional
from dataclasses import dataclass
from apps.core.core_exceptions.domain import DomainValidationException


class RegistrationType(Enum):
    PUBLIC = "public"
    STAFF = "staff"
    ADMIN = "admin"
    
    @classmethod
    def from_string(cls, value: str) -> 'RegistrationType':
        """Safely convert string to RegistrationType"""
        value_lower = value.lower()
        for reg_type in cls:
            if reg_type.value == value_lower:
                return reg_type
        raise ValueError(f"Invalid registration type: {value}")


@dataclass(frozen=True)
class RegistrationPolicy:
    """Immutable policy defining role creation rules"""
    registration_type: RegistrationType
    allowed_roles: Set[str]
    required_auth_roles: Set[str]
    requires_authentication: bool
    default_status: str
    needs_approval: bool
    
    def can_create_role(self, role: str, current_user_role: Optional[str] = None) -> bool:
        """Check if role can be created under this policy"""
        # Convert role to lowercase for case-insensitive comparison
        role_lower = role.lower()
        allowed_lower = {r.lower() for r in self.allowed_roles}
        
        # Validate role is allowed
        if role_lower not in allowed_lower:
            return False
        
        # Check authentication requirements
        if self.requires_authentication and not current_user_role:
            return False
        
        # Check permission requirements
        if self.requires_authentication:
            current_user_role_lower = current_user_role.lower() if current_user_role else ""
            required_auth_lower = {r.lower() for r in self.required_auth_roles}
            if current_user_role_lower not in required_auth_lower:
                return False
        
        return True
    
    def validate_role_for_registration(self, role: str, current_user_role: Optional[str] = None) -> None:
        """
        Validate role and raise exception if invalid.
        Use this in use cases for consistent error handling.
        """
        if not self.can_create_role(role, current_user_role):
            allowed_roles_str = ", ".join(sorted(self.allowed_roles))
            error_msg = f"Invalid role: {role} for registration type: {self.registration_type.value}. "
            error_msg += f"Allowed roles: {allowed_roles_str}"
            
            if self.requires_authentication:
                required_auth_str = ", ".join(sorted(self.required_auth_roles))
                error_msg += f" Requires authentication with roles: {required_auth_str}"
            
            raise DomainValidationException(
                message=error_msg,
                code="INVALID_ROLE_FOR_REGISTRATION",
                field="role"
            )


class RegistrationPolicyFactory:
    """Factory providing predefined registration policies"""
    
    @staticmethod
    def get_policy(registration_type: RegistrationType) -> RegistrationPolicy:
        """
        Get registration policy for the given type.
        Role names must match UserRole enum values (lowercase).
        """
        policies = {
            RegistrationType.PUBLIC: RegistrationPolicy(
                registration_type=RegistrationType.PUBLIC,
                allowed_roles={"visitor", "member"},  # Changed to lowercase, removed non-existent "user"
                required_auth_roles=set(),  # No auth required for public registration
                requires_authentication=False,
                default_status="pending",  # Matches UserStatus.PENDING
                needs_approval=True
            ),
            RegistrationType.STAFF: RegistrationPolicy(
                registration_type=RegistrationType.STAFF,
                allowed_roles={"staff", "ministry_leader"},  # Both can be created by admins
                required_auth_roles={"admin", "super_admin"},  # Must be authenticated as admin or super_admin
                requires_authentication=True,
                default_status="active",  # Matches UserStatus.ACTIVE
                needs_approval=False
            ),
            RegistrationType.ADMIN: RegistrationPolicy(
                registration_type=RegistrationType.ADMIN,
                allowed_roles={"admin", "super_admin"},  # Only high-level roles
                required_auth_roles={"super_admin"},  # Must be super_admin to create admin roles
                requires_authentication=True,
                default_status="active",  # Matches UserStatus.ACTIVE
                needs_approval=False
            )
        }
        
        if registration_type not in policies:
            raise ValueError(f"Unknown registration type: {registration_type}")
        
        return policies[registration_type]
    
    @staticmethod
    def get_all_policies() -> dict:
        """Get all available registration policies for reference"""
        return {
            reg_type.value: RegistrationPolicyFactory.get_policy(reg_type)
            for reg_type in RegistrationType
        }


# Helper functions for easy integration
def validate_registration(registration_type: str, role: str, 
                         current_user_role: Optional[str] = None) -> None:
    """
    Convenience function to validate registration.
    Use this in views or services for quick validation.
    """
    try:
        reg_type_enum = RegistrationType.from_string(registration_type)
        policy = RegistrationPolicyFactory.get_policy(reg_type_enum)
        policy.validate_role_for_registration(role, current_user_role)
    except ValueError as e:
        raise DomainValidationException(
            message=str(e),
            code="INVALID_REGISTRATION_TYPE",
            field="registration_type"
        )