#!/usr/bin/env python3
"""
Simple test to check the current state of the delegation system.
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
from users.permissions import can_approve_action_log
from django.utils import timezone

def test_current_state():
    """Test the current state of the delegation system"""
    print("=== TESTING CURRENT DELEGATION STATE ===")
    print("=" * 50)
    
    # Find users
    ag_cpap_user = User.objects.filter(designation__icontains='ag. c/pap', is_active=True).first()
    ag_acpap_user = User.objects.filter(designation__icontains='ag. ac/pap', is_active=True).first()
    
    if not ag_cpap_user or not ag_acpap_user:
        print("❌ Required users not found")
        return
    
    print(f"Ag. C/PAP User: {ag_cpap_user.get_full_name()}")
    print(f"Ag. AC/PAP User: {ag_acpap_user.get_full_name()}")
    
    # Check current state
    print(f"\n--- CURRENT STATE (NO DELEGATION) ---")
    print(f"Ag. C/PAP is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    print(f"Ag. C/PAP can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    print(f"Ag. AC/PAP has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    print(f"Ag. AC/PAP can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    
    # Create delegation
    print(f"\n--- CREATING DELEGATION ---")
    delegation = Delegation.objects.create(
        delegated_by=ag_cpap_user,
        delegated_to=ag_acpap_user,
        reason='leave',
        expires_at=timezone.now() + timedelta(days=7),
        is_active=True
    )
    print(f"Created delegation: {delegation}")
    
    # Check state after delegation
    print(f"\n--- STATE AFTER DELEGATION ---")
    print(f"Ag. C/PAP is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    print(f"Ag. C/PAP can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    print(f"Ag. AC/PAP has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    print(f"Ag. AC/PAP can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    
    # Test the permission function
    print(f"\n--- TESTING PERMISSION FUNCTION ---")
    ag_cpap_can_approve = can_approve_action_log(ag_cpap_user, None)
    ag_acpap_can_approve = can_approve_action_log(ag_acpap_user, None)
    
    print(f"can_approve_action_log(Ag. C/PAP): {ag_cpap_can_approve}")
    print(f"can_approve_action_log(Ag. AC/PAP): {ag_acpap_can_approve}")
    
    # Clean up
    delegation.delete()
    print(f"\n--- CLEANED UP ---")

if __name__ == "__main__":
    test_current_state()

