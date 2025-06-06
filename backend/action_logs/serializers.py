from rest_framework import serializers
from .models import ActionLog, ActionLogAssignmentHistory
from users.serializers import UserSerializer
from departments.serializers import DepartmentSerializer
from departments.models import Department
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

User = get_user_model()

class ActionLogSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=True
    )
    can_approve = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = ActionLog
        fields = [
            'id', 'title', 'description', 'department', 'department_id',
            'created_by', 'status', 'priority', 'due_date', 'assigned_to',
            'approved_by', 'approved_at', 'rejection_reason', 
            'created_at', 'updated_at', 'can_approve', 'comment_count'
        ]
        read_only_fields = [
            'created_by', 'approved_by', 'approved_at',
            'created_at', 'updated_at', 'comment_count'
        ]

    def get_can_approve(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.can_approve(request.user)
        return False

    def get_comment_count(self, obj):
        return obj.comments.count()

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        # Extract assigned_to before creating the instance
        assigned_to = validated_data.pop('assigned_to', [])
        
        # Get department from department_id
        department_id = validated_data.pop('department_id')
        try:
            department = Department.objects.get(id=department_id)
            validated_data['department'] = department
        except Department.DoesNotExist:
            raise serializers.ValidationError({
                'department_id': f'Department with id {department_id} does not exist'
            })
        
        # Create the action log instance
        instance = super().create(validated_data)
        
        # Add the assigned users
        if assigned_to:
            instance.assigned_to.set(assigned_to)
        
        return instance

    def validate(self, data):
        # Add any additional validation here
        if data.get('due_date') and data['due_date'] < timezone.now():
            raise serializers.ValidationError({
                'due_date': 'Due date cannot be in the past'
            })
        return data

class ActionLogApprovalSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        request = self.context.get('request')
        action_log = self.context.get('action_log')

        if not action_log.can_approve(request.user):
            raise serializers.ValidationError(
                "You don't have permission to approve/reject this action log"
            )

        return data

class ActionLogAssignmentHistorySerializer(serializers.ModelSerializer):
    assigned_by = UserSerializer(read_only=True)
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = ActionLogAssignmentHistory
        fields = ['id', 'action_log', 'assigned_by', 'assigned_to', 'assigned_at', 'comment']
        read_only_fields = ['action_log', 'assigned_by', 'assigned_at']

    def get_assigned_to(self, obj):
        try:
            users = obj.get_assigned_to_users()
            return UserSerializer(users, many=True).data
        except Exception as e:
            print(f"Error getting assigned_to users: {str(e)}")
            return []

    def to_representation(self, instance):
        try:
            print(f"Serializing assignment history record: {instance.id}")
            print(f"Assigned by: {instance.assigned_by}")
            print(f"Assigned to: {[user.id for user in instance.get_assigned_to_users()]}")
            
            data = super().to_representation(instance)
            print(f"Serialized data: {data}")
            return data
        except Exception as e:
            print(f"Error serializing assignment history record {instance.id}: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise 