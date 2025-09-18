#!/usr/bin/env python
"""
Development server startup script for Action Log System
This script creates test users and starts the Django development server
"""

import os
import sys
import django
import subprocess
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def create_test_users():
    """Create test users using Django management command"""
    try:
        from django.core.management import call_command
        print("Creating test users...")
        call_command('create_test_users')
        print("✅ Test users created successfully!")
    except Exception as e:
        print(f"⚠️  Warning: Could not create test users: {e}")
        print("You can manually create them later using: python manage.py create_test_users")

def start_server():
    """Start the Django development server"""
    print("Starting Django development server...")
    print("🌐 Server will be available at: http://localhost:8000")
    print("🔐 Test credentials will be available in the login page")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver'], cwd=backend_dir)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    print("🚀 Starting Action Log System Development Environment")
    print("=" * 60)
    
    # Create test users
    create_test_users()
    
    print("\n" + "=" * 60)
    
    # Start the server
    start_server()
