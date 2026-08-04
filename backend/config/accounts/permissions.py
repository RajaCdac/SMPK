from rest_framework.permissions import BasePermission

from .role_utils import user_is_admin


class IsAdminRole(BasePermission):
    """Allow Django superusers and users with ADMIN role assignment."""

    message = "Admin access required."

    def has_permission(self, request, view):
        return user_is_admin(request.user)
