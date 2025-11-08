# permissions.py
from django.db import models
from django.core.exceptions import PermissionDenied

class RoleBasedPermissionsMixin:
    """
    Mixin to add role-based permission checks to models
    """
    
    def can_create(self, user):
        """Check if user can create this type of object"""
        raise NotImplementedError("Subclasses must implement can_create")
    
    def can_view(self, user):
        """Check if user can view this object"""
        raise NotImplementedError("Subclasses must implement can_view")
    
    def can_edit(self, user):
        """Check if user can edit this object"""
        raise NotImplementedError("Subclasses must implement can_edit")
    
    def can_delete(self, user):
        """Check if user can delete this object"""
        raise NotImplementedError("Subclasses must implement can_delete")
    
    def check_can_create(self, user):
        """Raise PermissionDenied if user cannot create"""
        if not self.can_create(user):
            raise PermissionDenied("You do not have permission to create this resource")
    
    def check_can_view(self, user):
        """Raise PermissionDenied if user cannot view"""
        if not self.can_view(user):
            raise PermissionDenied("You do not have permission to view this resource")
    
    def check_can_edit(self, user):
        """Raise PermissionDenied if user cannot edit"""
        if not self.can_edit(user):
            raise PermissionDenied("You do not have permission to edit this resource")
    
    def check_can_delete(self, user):
        """Raise PermissionDenied if user cannot delete"""
        if not self.can_delete(user):
            raise PermissionDenied("You do not have permission to delete this resource")