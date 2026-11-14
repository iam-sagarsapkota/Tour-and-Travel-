from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.permissions import IsAdmin, IsSuperAdmin

__all__ = ["CanManageUser", "IsAdmin", "IsSuperAdmin"]


class CanManageUser(BasePermission):
    """Object-level rule for user management.

    Admins may read every account but only modify regular users; changing an
    admin or super-admin account requires a super admin.
    """

    message = "Only a super admin can modify admin accounts."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_super_admin:
            return True
        return not obj.is_admin
