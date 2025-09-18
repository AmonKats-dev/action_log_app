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
    This function now properly handles the leave delegation system:
    - Super admins and commissioners can always approve
    - Ag. C/PAP users can approve when not on leave
    - Ag. AC/PAP users can approve when they have leave delegation responsibilities
    - Department heads (assistant commissioners) can approve for their department
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin and commissioner can always approve
    if hasattr(user, 'is_super_admin') and user.is_super_admin:
        return True
    if hasattr(user, 'is_commissioner') and user.is_commissioner:
        return True
    
    # Use the User model's delegation-aware method
    if hasattr(user, 'can_approve_action_logs'):
        return user.can_approve_action_logs()
    
    # Fallback to basic role check for backward compatibility
    if hasattr(user, 'role') and user.role and user.role.can_approve:
        return True
    
    # Department head logic (assistant commissioner for the department)
    if (
        hasattr(user, 'department') and user.department == action_log.department and
        hasattr(user, 'role') and user.role and user.role.name == 'assistant_commissioner'
    ):
        return True
    
    return False 