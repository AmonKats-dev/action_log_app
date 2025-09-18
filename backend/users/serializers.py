from rest_framework import serializers
from .models import User, Role, LoginCode, Delegation
from departments.serializers import DepartmentSerializer, DepartmentUnitSerializer
from departments.models import DepartmentUnit
from django.utils import timezone

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class DelegationSerializer(serializers.ModelSerializer):
    delegated_by = serializers.SerializerMethodField()
    delegated_to = serializers.SerializerMethodField()
    delegated_to_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Delegation
        fields = [
            'id', 'delegated_by', 'delegated_to', 'delegated_at', 
            'expires_at', 'is_active', 'reason', 'delegated_to_id'
        ]
        read_only_fields = ['delegated_by', 'delegated_to', 'delegated_at']
    
    def get_delegated_by(self, obj):
        """Return only the full name without designation or employee ID"""
        if hasattr(obj, 'delegated_by') and obj.delegated_by:
            return obj.delegated_by.get_full_name()
        return ""
    
    def get_delegated_to(self, obj):
        """Return only the full name without designation or employee ID"""
        if hasattr(obj, 'delegated_to') and obj.delegated_to:
            return obj.delegated_to.get_full_name()
        return ""
    
    def to_representation(self, instance):
        """Custom representation to include delegated_to_id in read operations"""
        # If instance is a dictionary (validated_data), we need to handle it differently
        if isinstance(instance, dict):
            # For dictionary objects, just return the data with delegated_to_id
            data = dict(instance)
            if 'delegated_to_id' in data:
                data['delegated_to_id'] = data['delegated_to_id']
            return data
        
        # For model instances, use the normal serialization
        data = super().to_representation(instance)
        
        # Add delegated_to_id for read operations on model instances
        if hasattr(instance, 'delegated_to') and instance.delegated_to:
            data['delegated_to_id'] = instance.delegated_to.id
        else:
            data['delegated_to_id'] = None
            
        return data
    
    def validate(self, data):
        print(f"DEBUG: DelegationSerializer.validate called with data: {data}")
        
        # Check if the user being delegated to exists
        delegated_to_id = data.get('delegated_to_id')
        print(f"DEBUG: delegated_to_id from data: {delegated_to_id}")
        
        if delegated_to_id:
            try:
                from .models import User
                user = User.objects.get(id=delegated_to_id)
                print(f"DEBUG: Found target user: {user.username} (ID: {user.id})")
                if not user.is_active:
                    print(f"DEBUG: Target user is inactive")
                    raise serializers.ValidationError("Cannot delegate to an inactive user")
            except User.DoesNotExist:
                print(f"DEBUG: Target user with ID {delegated_to_id} does not exist")
                raise serializers.ValidationError("User to delegate to does not exist")
        
        # Check if expires_at is in the future
        expires_at = data.get('expires_at')
        print(f"DEBUG: expires_at from data: {expires_at}")
        print(f"DEBUG: expires_at type: {type(expires_at)}")
        
        if expires_at:
            try:
                current_time = timezone.now()
                print(f"DEBUG: Current time: {current_time}")
                print(f"DEBUG: expires_at parsed: {expires_at}")
                
                if expires_at <= current_time:
                    print(f"DEBUG: expires_at is in the past or present")
                    raise serializers.ValidationError("Expiration date must be in the future")
                else:
                    print(f"DEBUG: expires_at is in the future")
            except Exception as e:
                print(f"DEBUG: Error parsing expires_at: {e}")
                raise serializers.ValidationError(f"Invalid expiration date format: {expires_at}")
        
        # Validate leave delegation rules
        reason = data.get('reason', 'other')
        if reason == 'leave':
            # For leave delegations, ensure the delegate is Ag. AC/PAP
            if delegated_to_id:
                try:
                    target_user = User.objects.get(id=delegated_to_id)
                    if not target_user.has_ag_acpap_designation():
                        raise serializers.ValidationError(
                            "Leave delegations can only be made to Ag. AC/PAP users. "
                            f"User {target_user.get_full_name()} does not have Ag. AC/PAP designation."
                        )
                except User.DoesNotExist:
                    pass  # Already handled above
            
            # For leave delegations, expiration date is mandatory
            if not expires_at:
                raise serializers.ValidationError(
                    "Leave delegations must have an expiration date."
                )
        
        print(f"DEBUG: Validation passed successfully")
        return data

class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    department_unit = DepartmentUnitSerializer(read_only=True)
    can_create_action_logs = serializers.SerializerMethodField()
    can_create_action_logs_by_designation = serializers.SerializerMethodField()
    has_active_delegation = serializers.SerializerMethodField()
    has_ag_cpap_designation = serializers.SerializerMethodField()
    has_ag_acpap_designation = serializers.SerializerMethodField()
    can_manage_delegations = serializers.SerializerMethodField()
    has_leave_delegation_responsibilities = serializers.SerializerMethodField()
    can_approve_action_logs = serializers.SerializerMethodField()
    effective_approver = serializers.SerializerMethodField()
    current_effective_approver = serializers.SerializerMethodField()
    is_currently_on_leave = serializers.SerializerMethodField()
    leave_delegation_status = serializers.SerializerMethodField()
    delegation_transition_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role', 
            'department', 'department_unit', 'employee_id', 'phone_number', 
            'is_active', 'created_at', 'updated_at', 'designation',
            'can_create_action_logs', 'can_create_action_logs_by_designation', 'has_active_delegation',
            'has_ag_cpap_designation', 'has_ag_acpap_designation', 'can_manage_delegations',
            'has_leave_delegation_responsibilities', 'can_approve_action_logs', 'effective_approver',
            'current_effective_approver', 'is_currently_on_leave', 'leave_delegation_status',
            'delegation_transition_info'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_can_create_action_logs(self, obj):
        return obj.can_create_action_logs()
    
    def get_can_create_action_logs_by_designation(self, obj):
        return obj.can_create_action_logs_by_designation()
    
    def get_has_active_delegation(self, obj):
        active_delegation = obj.delegations_received.filter(is_active=True).first()
        if active_delegation:
            return {
                'id': active_delegation.id,
                'delegated_by': active_delegation.delegated_by.get_full_name(),
                'delegated_at': active_delegation.delegated_at,
                'expires_at': active_delegation.expires_at,
                'reason': active_delegation.reason,
                'is_valid': active_delegation.is_valid
            }
        return None

    def get_has_ag_cpap_designation(self, obj):
        return obj.has_ag_cpap_designation()
    
    def get_has_ag_acpap_designation(self, obj):
        return obj.has_ag_acpap_designation()
    
    def get_can_manage_delegations(self, obj):
        return obj.can_manage_delegations()

    def get_has_leave_delegation_responsibilities(self, obj):
        return obj.has_leave_delegation_responsibilities()

    def get_can_approve_action_logs(self, obj):
        return obj.can_approve_action_logs()

    def get_effective_approver(self, obj):
        effective_approver = obj.get_effective_approver_for_action_log()
        if effective_approver:
            return {
                'id': effective_approver.id,
                'name': effective_approver.get_full_name(),
                'username': effective_approver.username,
                'designation': effective_approver.designation,
                'is_leave_delegation': effective_approver != obj
            }
        return None

    def get_current_effective_approver(self, obj):
        """Get the current effective approver for action logs (who should handle approvals now)"""
        current_approver = obj.get_current_effective_approver()
        if current_approver:
            return {
                'id': current_approver.id,
                'name': current_approver.get_full_name(),
                'username': current_approver.username,
                'designation': current_approver.designation,
                'is_leave_delegation': current_approver != obj,
                'can_handle_approvals': current_approver.can_approve_action_logs()
            }
        return None

    def get_is_currently_on_leave(self, obj):
        """Check if this user is currently on leave"""
        return obj.is_currently_on_leave()

    def get_leave_delegation_status(self, obj):
        """Get detailed leave delegation status including expiration information"""
        return obj.get_leave_delegation_status()

    def get_delegation_transition_info(self, obj):
        """Get information about delegation transitions for UI display"""
        return obj.get_delegation_transition_info()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('email'):
            data['email'] = ''
        return data

    def validate(self, data):
        # If user is Commissioner or Assistant Commissioner, don't allow department unit
        if self.instance and self.instance.role and self.instance.role.name in ['commissioner', 'assistant_commissioner']:
            data['department_unit'] = None
        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user 