from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Department, DepartmentUnit
from .serializers import DepartmentSerializer, DepartmentUnitSerializer
from users.permissions import IsSuperAdminOrReadOnly

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsSuperAdminOrReadOnly]

    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        department = self.get_object()
        units = DepartmentUnit.objects.filter(department=department)
        serializer = DepartmentUnitSerializer(units, many=True)
        return Response(serializer.data)

class DepartmentUnitViewSet(viewsets.ModelViewSet):
    queryset = DepartmentUnit.objects.all()
    serializer_class = DepartmentUnitSerializer
    permission_classes = [IsSuperAdminOrReadOnly]

    def get_queryset(self):
        queryset = DepartmentUnit.objects.all()
        department_id = self.request.query_params.get('department', None)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset 