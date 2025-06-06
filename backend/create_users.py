import os
import django
import requests
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile

# Create IN department unit users
in_users = [
    {
        'username': 'in_head',
        'password': 'inhead123',
        'email': 'in.head@example.com',
        'first_name': 'IN',
        'last_name': 'Head',
        'department': 1,
        'department_unit': 1,
        'is_head': True,
        'is_active': True
    },
    {
        'username': 'in_staff1',
        'password': 'instaff123',
        'email': 'in.staff1@example.com',
        'first_name': 'IN',
        'last_name': 'Staff1',
        'department': 1,
        'department_unit': 1,
        'is_head': False,
        'is_active': True
    },
    {
        'username': 'in_staff2',
        'password': 'instaff123',
        'email': 'in.staff2@example.com',
        'first_name': 'IN',
        'last_name': 'Staff2',
        'department': 1,
        'department_unit': 1,
        'is_head': False,
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
        'department': 1,
        'department_unit': 2,
        'is_head': True,
        'is_active': True
    },
    {
        'username': 'pas_staff1',
        'password': 'passtaff123',
        'email': 'pas.staff1@example.com',
        'first_name': 'PAS',
        'last_name': 'Staff1',
        'department': 1,
        'department_unit': 2,
        'is_head': False,
        'is_active': True
    },
    {
        'username': 'pas_staff2',
        'password': 'passtaff123',
        'email': 'pas.staff2@example.com',
        'first_name': 'PAS',
        'last_name': 'Staff2',
        'department': 1,
        'department_unit': 2,
        'is_head': False,
        'is_active': True
    }
]

def create_user(user_data):
    try:
        # Create Django User
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name']
        )
        
        # Create UserProfile
        UserProfile.objects.create(
            user=user,
            department=user_data['department'],
            department_unit=user_data['department_unit'],
            is_head=user_data['is_head'],
            is_active=user_data['is_active']
        )
        
        print(f"Successfully created user: {user_data['username']}")
    except Exception as e:
        print(f"Error creating user {user_data['username']}: {str(e)}")

# Create all users
print("Creating IN department unit users...")
for user_data in in_users:
    create_user(user_data)

print("\nCreating PAS department unit users...")
for user_data in pas_users:
    create_user(user_data)

print("\nUser creation completed!") 