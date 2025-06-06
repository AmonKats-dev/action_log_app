from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a Senior Economist user'

    def handle(self, *args, **kwargs):
        # Create or get the Senior Economist role
        role, created = Role.objects.get_or_create(
            name=Role.SENIOR_ECONOMIST,
            defaults={
                'can_create_logs': True,
                'can_update_status': True,
                'can_approve': True,
                'can_view_all_logs': True,
                'can_configure': False
            }
        )

        # Create the Senior Economist user
        username = 'senior_economist1'
        email = 'senior_economist1@example.com'
        password = 'senior123'  # This will be hashed by Django

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Senior',
                last_name='Economist',
                role=role,
                employee_id='SE001',
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created Senior Economist user: {username}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Login credentials:\nUsername: {username}\nPassword: {password}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'User {username} already exists')
            ) 