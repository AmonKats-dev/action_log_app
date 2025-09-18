from rest_framework import permissions

class IsSuperAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_super_admin

class IsDepartmentUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        return obj.department == request.user.department

class CanManageUsers(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (request.user.is_super_admin or 
                request.user.is_commissioner or 
                request.user.is_assistant_commissioner)

def can_approve_action_log(user, action_log):
    """
    Returns True if the user can approve the given action log.
    Typically, this means the user is a super admin, commissioner,
    or the assistant commissioner (department head) of the action log's department.
    """
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, 'is_super_admin') and user.is_super_admin:
        return True
    if hasattr(user, 'is_commissioner') and user.is_commissioner:
        return True
    # Department head logic (assistant commissioner for the department)
    if (
        hasattr(user, 'department') and user.department == action_log.department and
        hasattr(user, 'role') and user.role and user.role.name == 'assistant_commissioner'
    ):
        return True
    return False 