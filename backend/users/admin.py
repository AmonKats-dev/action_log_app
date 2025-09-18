from django.contrib import admin
from .models import User, Role, Delegation

@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'delegated_by_name', 'delegated_to_name', 'reason', 'delegated_at', 
        'expires_at', 'is_active', 'is_expired', 'is_valid', 'is_leave_delegation'
    ]
    list_filter = [
        'reason', 'is_active', 'delegated_at', 'expires_at', 
        'delegated_by', 'delegated_to'
    ]
    search_fields = [
        'delegated_by__username', 'delegated_by__first_name', 'delegated_by__last_name',
        'delegated_to__username', 'delegated_to__first_name', 'delegated_to__last_name',
        'reason'
    ]
    readonly_fields = ['delegated_at', 'is_expired', 'is_valid', 'is_leave_delegation']
    date_hierarchy = 'delegated_at'
    ordering = ['-delegated_at']
    
    fieldsets = (
        ('Delegation Details', {
            'fields': ('delegated_by', 'delegated_to', 'reason')
        }),
        ('Timing', {
            'fields': ('delegated_at', 'expires_at')
        }),
        ('Status', {
            'fields': ('is_active', 'is_expired', 'is_valid', 'is_leave_delegation')
        }),
    )
    
    def delegated_by_name(self, obj):
        """Display only the full name without designation"""
        if obj.delegated_by:
            return obj.delegated_by.get_full_name()
        return ""
    delegated_by_name.short_description = 'Delegated By'
    delegated_by_name.admin_order_field = 'delegated_by__first_name'
    
    def delegated_to_name(self, obj):
        """Display only the full name without designation"""
        if obj.delegated_to:
            return obj.delegated_to.get_full_name()
        return ""
    delegated_to_name.short_description = 'Delegated To'
    delegated_to_name.admin_order_field = 'delegated_to__first_name'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Valid'

    def is_leave_delegation(self, obj):
        return obj.is_leave_delegation()
    is_leave_delegation.boolean = True
    is_leave_delegation.short_description = 'Leave Delegation'

admin.site.register(User)
admin.site.register(Role) 