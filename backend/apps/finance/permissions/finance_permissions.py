"""Permissions for finance-related API endpoints."""

from apps.accounts.permissions.role_permission import (
    IsPastorOrAdministrator,
)


class CanManageFinance(IsPastorOrAdministrator):
    """Allow active Pastors and Administrators to access financial data."""
