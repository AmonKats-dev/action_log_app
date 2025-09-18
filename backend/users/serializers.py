from rest_framework import serializers
from .models import User, Role
from departments.serializers import DepartmentUnitSerializer
from departments.models import DepartmentUnit

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'can_create_logs', 'can_update_status', 
                 'can_approve', 'can_view_all_logs', 'can_configure']

class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    department_unit = DepartmentUnitSerializer(read_only=True)
    department_unit_id = serializers.PrimaryKeyRelatedField(
        queryset=DepartmentUnit.objects.all(),
        source='department_unit',
        write_only=True,
        required=False,
        allow_null=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'department_unit', 'department_unit_id',
            'employee_id', 'phone_number', 'is_active', 'designation'
        ]
        read_only_fields = ['id', 'role', 'department']
        extra_kwargs = {
            'password': {'write_only': True}
        }

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