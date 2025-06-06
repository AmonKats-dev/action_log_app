from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.name} ({self.code})"

class DepartmentUnit(models.Model):
    INFRASTRUCTURE = 'infrastructure'
    PUBLIC_ADMIN = 'public_admin'
    SOCIAL_SERVICES = 'social_services'

    UNIT_TYPE_CHOICES = [
        (INFRASTRUCTURE, 'Infrastructure'),
        (PUBLIC_ADMIN, 'Public Administration'),
        (SOCIAL_SERVICES, 'Social Services'),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=100)
    unit_type = models.CharField(max_length=50, choices=UNIT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Department Unit'
        verbose_name_plural = 'Department Units'
        unique_together = ['department', 'name']

    def __str__(self):
        return f"{self.name} - {self.department.name}" 