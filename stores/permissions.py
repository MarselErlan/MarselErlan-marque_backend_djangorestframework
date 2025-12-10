"""
Custom permissions for store management.
"""

from rest_framework import permissions


class IsStoreOwner(permissions.BasePermission):
    """
    Permission to check if user owns a store.
    Superusers can access everything.
    """
    
    def has_permission(self, request, view):
        """Check if user has permission to access store endpoints"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers can access everything
        if request.user.is_superuser:
            return True
        
        # Check if user owns at least one active store
        return request.user.owned_stores.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission for a specific store object"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers can access everything
        if request.user.is_superuser:
            return True
        
        # Check if user owns this store
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # For product objects, check if user owns the product's store
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        
        return False


class IsStoreOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow store owners to edit, others can only read.
    """
    
    def has_permission(self, request, view):
        """Check if user has permission"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers can do everything
        if request.user.is_superuser:
            return True
        
        # Store owners can write
        return request.user.owned_stores.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission for a specific object"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers can do everything
        if request.user.is_superuser:
            return True
        
        # Check if user owns the store
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False

