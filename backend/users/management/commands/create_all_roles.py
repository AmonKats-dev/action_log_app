from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates users for all roles'

    def handle(self, *args, **kwargs):
        # Define role configurations
        role_configs = {
            Role.PRINCIPAL_ECONOMIST: {
                'username': 'principal_economist1',
                'email': 'principal_economist1@example.com',
                'password': 'principal123',
                'first_name': 'Principal',
                'last_name': 'Economist',
                'employee_id': 'PE001',
                'permissions': {
                    'can_create_logs': True,
                    'can_update_status': True,
                    'can_approve': True,
                    'can_view_all_logs': True,
                    'can_configure': True
                }
            },
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
                    'can_configure': True
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
                    'can_update_status': True,
                    'can_approve': True,
                    'can_view_all_logs': True,
                    'can_configure': True
                }
            },
            Role.SUPER_ADMIN: {
                'username': 'super_admin1',
                'email': 'super_admin1@example.com',
                'password': 'super123',
                'first_name': 'Super',
                'last_name': 'Admin',
                'employee_id': 'SA001',
                'permissions': {
                    'can_create_logs': True,
                    'can_update_status': True,
                    'can_approve': True,
                    'can_view_all_logs': True,
                    'can_configure': True
                }
            }
        }

        # Create users for each role
        for role_name, config in role_configs.items():
            # Create or get the role
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults=config['permissions']
            )

            # Create the user if it doesn't exist
            if not User.objects.filter(username=config['username']).exists():
                user = User.objects.create_user(
                    username=config['username'],
                    email=config['email'],
                    password=config['password'],
                    first_name=config['first_name'],
                    last_name=config['last_name'],
                    role=role,
                    employee_id=config['employee_id'],
                    is_active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created {role_name} user: {config["username"]}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Login credentials:\nUsername: {config["username"]}\nPassword: {config["password"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User {config["username"]} already exists')
                ) 