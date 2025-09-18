from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from departments.models import Department, DepartmentUnit
from django.core.validators import RegexValidator

class Role(models.Model):
    ECONOMIST = 'economist'
    SENIOR_ECONOMIST = 'senior_economist'
    PRINCIPAL_ECONOMIST = 'principal_economist'
    ASSISTANT_COMMISSIONER = 'assistant_commissioner'
    COMMISSIONER = 'commissioner'
    SUPER_ADMIN = 'super_admin'

    ROLE_CHOICES = [
        (ECONOMIST, 'Economist'),
        (SENIOR_ECONOMIST, 'Senior Economist'),
        (PRINCIPAL_ECONOMIST, 'Principal Economist'),
        (ASSISTANT_COMMISSIONER, 'Assistant Commissioner'),
        (COMMISSIONER, 'Commissioner'),
        (SUPER_ADMIN, 'Super Admin'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    can_create_logs = models.BooleanField(default=True)
    can_update_status = models.BooleanField(default=True)
    can_approve = models.BooleanField(default=False)
    can_view_all_logs = models.BooleanField(default=False)
    can_configure = models.BooleanField(default=False)
    can_view_all_users = models.BooleanField(default=False)
    can_assign_to_commissioner = models.BooleanField(default=False)

    def __str__(self):
        return self.get_name_display()

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True)
    department = models.ForeignKey('departments.Department', on_delete=models.PROTECT, null=True)
    employee_id = models.CharField(max_length=50, unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    department_unit = models.ForeignKey(
        DepartmentUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    designation = models.CharField(max_length=100, blank=True, null=True)  # User's title/designation
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def save(self, *args, **kwargs):
        # If user is Commissioner or Assistant Commissioner, don't assign department unit
        if self.role and self.role.name in ['commissioner', 'assistant_commissioner']:
            self.department_unit = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"

    @property
    def is_economist(self):
        return self.role.name == Role.ECONOMIST

    @property
    def is_senior_economist(self):
        return self.role.name == Role.SENIOR_ECONOMIST

    @property
    def is_principal_economist(self):
        return self.role.name == Role.PRINCIPAL_ECONOMIST

    @property
    def is_assistant_commissioner(self):
        return self.role.name == Role.ASSISTANT_COMMISSIONER

    @property
    def is_commissioner(self):
        return self.role.name == Role.COMMISSIONER

    @property
    def is_super_admin(self):
        return self.role.name == Role.SUPER_ADMIN

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users' 