from django.core.management.base import BaseCommand
from users.models import User, Role
from departments.models import Department, DepartmentUnit

class Command(BaseCommand):
    help = 'Creates test users for IN and PAS department units'

    def handle(self, *args, **kwargs):
        # Get or create the Economist role
        economist_role, _ = Role.objects.get_or_create(
            name=Role.ECONOMIST,
            defaults={
                'can_create_logs': True,
                'can_update_status': True,
                'can_approve': False,
                'can_view_all_logs': False,
                'can_configure': False,
                'can_view_all_users': False,
                'can_assign_to_commissioner': False
            }
        )

        # Get the department
        department = Department.objects.get(id=1)

        # Create IN department unit users
        in_users = [
            {
                'username': 'in_head',
                'password': 'inhead123',
                'email': 'in.head@example.com',
                'first_name': 'IN',
                'last_name': 'Head',
                'employee_id': 'IN001',
                'phone_number': '+1234567890',
                'designation': 'Head of IN Unit',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=1),
                'role': economist_role,
                'is_active': True
            },
            {
                'username': 'in_staff1',
                'password': 'instaff123',
                'email': 'in.staff1@example.com',
                'first_name': 'IN',
                'last_name': 'Staff1',
                'employee_id': 'IN002',
                'phone_number': '+1234567891',
                'designation': 'IN Staff',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=1),
                'role': economist_role,
                'is_active': True
            },
            {
                'username': 'in_staff2',
                'password': 'instaff123',
                'email': 'in.staff2@example.com',
                'first_name': 'IN',
                'last_name': 'Staff2',
                'employee_id': 'IN003',
                'phone_number': '+1234567892',
                'designation': 'IN Staff',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=1),
                'role': economist_role,
                'is_active': True
            }
        ]

        # Create PAS department unit users
        pas_users = [
            {
                'username': 'pas_head',
                'password': 'pashead123',
                'email': 'pas.head@example.com',
                'first_name': 'PAS',
                'last_name': 'Head',
                'employee_id': 'PAS001',
                'phone_number': '+1234567893',
                'designation': 'Head of PAS Unit',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=2),
                'role': economist_role,
                'is_active': True
            },
            {
                'username': 'pas_staff1',
                'password': 'passtaff123',
                'email': 'pas.staff1@example.com',
                'first_name': 'PAS',
                'last_name': 'Staff1',
                'employee_id': 'PAS002',
                'phone_number': '+1234567894',
                'designation': 'PAS Staff',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=2),
                'role': economist_role,
                'is_active': True
            },
            {
                'username': 'pas_staff2',
                'password': 'passtaff123',
                'email': 'pas.staff2@example.com',
                'first_name': 'PAS',
                'last_name': 'Staff2',
                'employee_id': 'PAS003',
                'phone_number': '+1234567895',
                'designation': 'PAS Staff',
                'department': department,
                'department_unit': DepartmentUnit.objects.get(id=2),
                'role': economist_role,
                'is_active': True
            }
        ]

        def create_user(user_data):
            try:
                # Create User
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    employee_id=user_data['employee_id'],
                    phone_number=user_data['phone_number'],
                    designation=user_data['designation'],
                    department=user_data['department'],
                    department_unit=user_data['department_unit'],
                    role=user_data['role'],
                    is_active=user_data['is_active']
                )
                
                self.stdout.write(self.style.SUCCESS(f"Successfully created user: {user_data['username']}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating user {user_data['username']}: {str(e)}"))

        # Create all users
        self.stdout.write("Creating IN department unit users...")
        for user_data in in_users:
            create_user(user_data)

        self.stdout.write("Creating PAS department unit users...")
        for user_data in pas_users:
            create_user(user_data)

        self.stdout.write(self.style.SUCCESS("User creation completed!")) 