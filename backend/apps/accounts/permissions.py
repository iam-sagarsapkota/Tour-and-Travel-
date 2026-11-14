from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Admin or super admin."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_super_admin)


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
