#!/usr/bin/env python3
"""
Debug script to investigate delegation logic issues.
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

def debug_delegation():
    """Debug the delegation logic"""
    print("=== DEBUGGING DELEGATION LOGIC ===")
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
    print(f"\n--- CURRENT STATE ---")
    print(f"Ag. C/PAP is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    print(f"Ag. C/PAP can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    print(f"Ag. AC/PAP has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    print(f"Ag. AC/PAP can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    
    # Check delegations
    print(f"\n--- DELEGATIONS ---")
    delegations_given = ag_cpap_user.delegations_given.all()
    delegations_received = ag_acpap_user.delegations_received.all()
    
    print(f"Ag. C/PAP delegations given: {delegations_given.count()}")
    for d in delegations_given:
        print(f"  - To: {d.delegated_to.get_full_name()}, Reason: {d.reason}, Active: {d.is_active}, Expires: {d.expires_at}")
    
    print(f"Ag. AC/PAP delegations received: {delegations_received.count()}")
    for d in delegations_received:
        print(f"  - From: {d.delegated_by.get_full_name()}, Reason: {d.reason}, Active: {d.is_active}, Expires: {d.expires_at}")
    
    # Create a new delegation
    print(f"\n--- CREATING NEW DELEGATION ---")
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
    
    # Check the specific query in is_currently_on_leave
    print(f"\n--- DEBUGGING is_currently_on_leave QUERY ---")
    leave_delegations = ag_cpap_user.delegations_given.filter(
        is_active=True,
        reason='leave',
        expires_at__gt=timezone.now()
    )
    print(f"Leave delegations query result count: {leave_delegations.count()}")
    for d in leave_delegations:
        print(f"  - Delegation ID: {d.id}, Active: {d.is_active}, Reason: {d.reason}, Expires: {d.expires_at}")
        print(f"    Now: {timezone.now()}")
        print(f"    expires_at > now: {d.expires_at > timezone.now()}")
    
    # Check the specific query in has_leave_delegation_responsibilities
    print(f"\n--- DEBUGGING has_leave_delegation_responsibilities QUERY ---")
    leave_delegations_received = ag_acpap_user.delegations_received.filter(
        is_active=True,
        reason='leave',
        expires_at__gt=timezone.now()
    )
    print(f"Leave delegations received query result count: {leave_delegations_received.count()}")
    for d in leave_delegations_received:
        print(f"  - Delegation ID: {d.id}, Active: {d.is_active}, Reason: {d.reason}, Expires: {d.expires_at}")
        print(f"    Now: {timezone.now()}")
        print(f"    expires_at > now: {d.expires_at > timezone.now()}")
    
    # Clean up
    delegation.delete()
    print(f"\n--- CLEANED UP ---")

if __name__ == "__main__":
    debug_delegation()

