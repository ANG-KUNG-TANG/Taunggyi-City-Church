from typing import Optional
from .config import UseCaseConfiguration

class AuthorizationManager:

    @staticmethod
    def is_authorized(user, config: UseCaseConfiguration) -> bool:
        if not config.require_authentication:
            return True

        if not user or not user.is_active:
            return False

        if config.required_roles and user.role not in config.required_roles:
            return False

        if config.required_permissions:
            perms = user.get_permissions()
            return all(perms.get(p, False) for p in config.required_permissions)

        return True
