from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Role
from .serializers import UserSerializer, RoleSerializer
from .permissions import IsSuperAdminOrReadOnly

User = get_user_model()

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperAdminOrReadOnly]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        
        # Get filters from query params
        department_id = self.request.query_params.get('department')
        department_unit_id = self.request.query_params.get('department_unit')
        
        print(f"Request from user {user.username} (dept: {user.department_id})")
        print(f"Filters - department: {department_id}, unit: {department_unit_id}")
        
        # Apply department filter if specified
        if department_id:
            queryset = queryset.filter(department_id=department_id)
            print(f"Filtered queryset by department {department_id}")
        
        # Apply department unit filter if specified
        if department_unit_id:
            queryset = queryset.filter(department_unit_id=department_unit_id)
            print(f"Filtered queryset by department unit {department_unit_id}")
        
        # Apply role-based filtering
        if hasattr(user, 'is_super_admin') and user.is_super_admin:
            print(f"User {user.username} is super admin, returning all users")
            return queryset
        elif hasattr(user, 'role') and user.role and user.role.can_view_all_users:
            # Commissioner and Assistant Commissioner can view all users
            print(f"User {user.username} has view_all_users permission")
            return queryset
        elif hasattr(user, 'department_unit') and user.department_unit:
            # Department unit head can only view users in their unit
            print(f"User {user.username} is department unit head, filtering by unit {user.department_unit_id}")
            return queryset.filter(department_unit=user.department_unit)
        else:
            # For other roles, they can only see users in their department
            print(f"User {user.username} is regular user, filtering by department {user.department_id}")
            return queryset.filter(department=user.department)

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        
        # Check if user has permission to assign to commissioner
        if data.get('role') and data['role'].name == 'commissioner':
            if not (user.role and user.role.can_assign_to_commissioner):
                raise permissions.PermissionDenied("You don't have permission to assign commissioner role")
        
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        
        # Check if user has permission to assign to commissioner
        if data.get('role') and data['role'].name == 'commissioner':
            if not (user.role and user.role.can_assign_to_commissioner):
                raise permissions.PermissionDenied("You don't have permission to assign commissioner role")
        
        serializer.save()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def department_users(self, request):
        if not request.user.department:
            return Response(
                {"error": "User is not assigned to any department"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(department=request.user.department)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def department_unit_users(self, request):
        if not request.user.department_unit:
            return Response(
                {"error": "User is not assigned to any department unit"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(department_unit=request.user.department_unit)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data) 