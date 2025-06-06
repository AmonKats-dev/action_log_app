from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role
from departments.models import Department, DepartmentUnit

User = get_user_model()

class Command(BaseCommand):
    help = 'Recreates Commissioner and Assistant Commissioner roles with proper permissions'

    def handle(self, *args, **kwargs):
        # Define role configurations
        role_configs = {
            Role.ASSISTANT_COMMISSIONER: {
                'username': 'assistant_commissioner1',
                'email': 'assistant_commissioner1@example.com',
                'password': 'assistant123',
                'first_name': 'Assistant',
                'last_name': 'Commissioner',
                'employee_id': 'AC001',
                'permissions': {
                    'can_create_logs': True,
                    'can_update_status': True,
                    'can_approve': True,
                    'can_view_all_logs': True,
                    'can_configure': False,
                    'can_view_all_users': True,
                    'can_assign_to_commissioner': False
                }
            },
            Role.COMMISSIONER: {
                'username': 'commissioner1',
                'email': 'commissioner1@example.com',
                'password': 'commissioner123',
                'first_name': 'Commissioner',
                'last_name': 'Chief',
                'employee_id': 'C001',
                'permissions': {
                    'can_create_logs': True,
                    'can_update_status': False,
                    'can_approve': True,
                    'can_view_all_logs': True,
                    'can_configure': False,
                    'can_view_all_users': True,
                    'can_assign_to_commissioner': True
                }
            }
        }

        # Get all departments
        departments = Department.objects.all()
        
        if not departments.exists():
            self.stdout.write(
                self.style.ERROR('No departments found. Please create departments first.')
            )
            return

        # Create or update roles and users for each department
        for department in departments:
            self.stdout.write(f'Processing department: {department.name}')
            
            for role_name, config in role_configs.items():
                # Create or update the role
                role, created = Role.objects.get_or_create(
                    name=role_name,
                    defaults=config['permissions']
                )
                
                if not created:
                    # Update existing role permissions
                    for key, value in config['permissions'].items():
                        setattr(role, key, value)
                    role.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated {role_name} role permissions')
                    )

                # Create department-specific username
                dept_username = f"{config['username']}_{department.name.lower().replace(' ', '_')}"
                
                # Create the user if it doesn't exist
                if not User.objects.filter(username=dept_username).exists():
                    user = User.objects.create_user(
                        username=dept_username,
                        email=config['email'],
                        password=config['password'],
                        first_name=config['first_name'],
                        last_name=config['last_name'],
                        role=role,
                        employee_id=f"{config['employee_id']}_{department.id}",
                        department=department,
                        is_active=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully created {role_name} user for {department.name}: {dept_username}')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Login credentials:\nUsername: {dept_username}\nPassword: {config["password"]}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'User {dept_username} already exists')
                    )

        self.stdout.write(
            self.style.SUCCESS('Successfully recreated Commissioner and Assistant Commissioner roles')
        ) 