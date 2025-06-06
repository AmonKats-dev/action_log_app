from rest_framework import serializers
from .models import Department, DepartmentUnit

class DepartmentUnitSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = DepartmentUnit
        fields = ['id', 'name', 'unit_type', 'description', 
                 'department', 'department_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DepartmentSerializer(serializers.ModelSerializer):
    units = DepartmentUnitSerializer(many=True, read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'description', 
                 'units', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at'] 