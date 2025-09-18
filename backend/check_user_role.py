#!/usr/bin/env python3
"""
Script to check user role and permissions.
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User, Delegation
from django.utils import timezone

def check_user_role():
    """Check user role and permissions"""
    print("=== CHECKING USER ROLE AND PERMISSIONS ===")
    print("=" * 50)
    
    # Find users
    ag_cpap_user = User.objects.filter(designation__icontains='ag. c/pap', is_active=True).first()
    ag_acpap_user = User.objects.filter(designation__icontains='ag. ac/pap', is_active=True).first()
    
    if not ag_cpap_user or not ag_acpap_user:
        print("❌ Required users not found")
        return
    
    print(f"Ag. C/PAP User: {ag_cpap_user.get_full_name()}")
    print(f"Ag. AC/PAP User: {ag_acpap_user.get_full_name()}")
    
    # Check Ag. C/PAP user details
    print(f"\n--- Ag. C/PAP User Details ---")
    print(f"  Role: {ag_cpap_user.role.name if ag_cpap_user.role else 'None'}")
    print(f"  is_super_admin: {ag_cpap_user.is_super_admin}")
    print(f"  is_commissioner: {ag_cpap_user.is_commissioner}")
    print(f"  is_assistant_commissioner: {ag_cpap_user.is_assistant_commissioner}")
    print(f"  has_ag_cpap_designation: {ag_cpap_user.has_ag_cpap_designation()}")
    print(f"  is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    print(f"  can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    
    # Check delegations
    delegations = ag_cpap_user.delegations_given.filter(is_active=True)
    print(f"  Active delegations: {delegations.count()}")
    for d in delegations:
        print(f"    - To: {d.delegated_to.get_full_name()}, Reason: {d.reason}, Expires: {d.expires_at}")
    
    # Check Ag. AC/PAP user details
    print(f"\n--- Ag. AC/PAP User Details ---")
    print(f"  Role: {ag_acpap_user.role.name if ag_acpap_user.role else 'None'}")
    print(f"  is_super_admin: {ag_acpap_user.is_super_admin}")
    print(f"  is_commissioner: {ag_acpap_user.is_commissioner}")
    print(f"  is_assistant_commissioner: {ag_acpap_user.is_assistant_commissioner}")
    print(f"  has_ag_acpap_designation: {ag_acpap_user.has_ag_acpap_designation()}")
    print(f"  has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    print(f"  can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    
    # Check delegations received
    delegations_received = ag_acpap_user.delegations_received.filter(is_active=True)
    print(f"  Active delegations received: {delegations_received.count()}")
    for d in delegations_received:
        print(f"    - From: {d.delegated_by.get_full_name()}, Reason: {d.reason}, Expires: {d.expires_at}")

if __name__ == "__main__":
    check_user_role()

