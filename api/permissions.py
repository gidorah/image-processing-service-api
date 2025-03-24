from django.contrib.auth import authenticate, get_user_model
from rest_framework import permissions

User = get_user_model()


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Return True if the user is the owner of the object.
        """
        return obj.owner == request.user
