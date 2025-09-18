#!/usr/bin/env python3
"""
Test script to create a fresh delegation and monitor the is_active field.
"""

import os
import sys
import django
from datetime import timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User, Delegation
from django.utils import timezone

def test_fresh_delegation():
    """Test creating a fresh delegation and monitor is_active"""
    print("=== TESTING FRESH DELEGATION CREATION ===")
    print("=" * 50)
    
    # Find users
    ag_cpap_user = User.objects.filter(designation__icontains='ag. c/pap', is_active=True).first()
    ag_acpap_user = User.objects.filter(designation__icontains='ag. ac/pap', is_active=True).first()
    
    if not ag_cpap_user or not ag_acpap_user:
        print("❌ Required users not found")
        return
    
    print(f"Ag. C/PAP User: {ag_cpap_user.get_full_name()}")
    print(f"Ag. AC/PAP User: {ag_acpap_user.get_full_name()}")
    
    # Clean up any existing delegations between these users
    existing_delegations = Delegation.objects.filter(
        delegated_by=ag_cpap_user,
        delegated_to=ag_acpap_user
    )
    if existing_delegations.exists():
        print(f"Cleaning up {existing_delegations.count()} existing delegations")
        existing_delegations.delete()
    
    # Create a new delegation
    print(f"\n--- CREATING NEW DELEGATION ---")
    print(f"Current time: {timezone.now()}")
    
    delegation = Delegation(
        delegated_by=ag_cpap_user,
        delegated_to=ag_acpap_user,
        reason='leave',
        expires_at=timezone.now() + timedelta(days=7),
        is_active=True
    )
    
    print(f"Before save:")
    print(f"  is_active: {delegation.is_active}")
    print(f"  expires_at: {delegation.expires_at}")
    print(f"  expires_at > now: {delegation.expires_at > timezone.now()}")
    
    # Save the delegation
    delegation.save()
    
    print(f"\nAfter save:")
    print(f"  is_active: {delegation.is_active}")
    print(f"  expires_at: {delegation.expires_at}")
    print(f"  expires_at > now: {delegation.expires_at > timezone.now()}")
    
    # Refresh from database
    delegation.refresh_from_db()
    print(f"\nAfter refresh from database:")
    print(f"  is_active: {delegation.is_active}")
    print(f"  expires_at: {delegation.expires_at}")
    
    # Test the user methods
    print(f"\n--- TESTING USER METHODS ---")
    print(f"Ag. C/PAP is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    print(f"Ag. C/PAP can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    print(f"Ag. AC/PAP has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    print(f"Ag. AC/PAP can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    
    # Clean up
    delegation.delete()
    print(f"\n--- CLEANED UP ---")

if __name__ == "__main__":
    test_fresh_delegation()

