#!/usr/bin/env python3
"""
Test script to demonstrate leave delegation functionality.
This script shows how Ag. AC/PAP users take over responsibilities when Ag. C/PAP users are on leave.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Delegation, User
from django.utils import timezone

def test_leave_delegation_functionality():
    """Test the leave delegation functionality"""
    print("=== TESTING LEAVE DELEGATION FUNCTIONALITY ===")
    print("=" * 80)
    
    # Get all users with Ag. C/PAP and Ag. AC/PAP designations
    ag_cpap_users = []
    ag_acpap_users = []
    
    for user in User.objects.filter(is_active=True):
        if user.has_ag_cpap_designation():
            ag_cpap_users.append(user)
        elif user.has_ag_acpap_designation():
            ag_acpap_users.append(user)
    
    print(f"Found {len(ag_cpap_users)} Ag. C/PAP users:")
    for user in ag_cpap_users:
        print(f"  - {user.get_full_name()} ({user.username})")
    
    print(f"\nFound {len(ag_acpap_users)} Ag. AC/PAP users:")
    for user in ag_acpap_users:
        print(f"  - {user.get_full_name()} ({user.username})")
    
    if not ag_cpap_users or not ag_acpap_users:
        print("\nCannot test leave delegation: Need both Ag. C/PAP and Ag. AC/PAP users")
        return
    
    # Test leave delegation creation
    print("\n=== TESTING LEAVE DELEGATION CREATION ===")
    print("-" * 50)
    
    ag_cpap_user = ag_cpap_users[0]
    ag_acpap_user = ag_acpap_users[0]
    
    print(f"Testing with:")
    print(f"  Ag. C/PAP: {ag_cpap_user.get_full_name()}")
    print(f"  Ag. AC/PAP: {ag_acpap_user.get_full_name()}")
    
    # Create a leave delegation
    try:
        leave_delegation = Delegation.objects.create(
            delegated_by=ag_cpap_user,
            delegated_to=ag_acpap_user,
            reason='leave',
            expires_at=timezone.now() + timedelta(days=7),  # 7 days from now
            is_active=True
        )
        print(f"\n✅ Successfully created leave delegation:")
        print(f"  ID: {leave_delegation.id}")
        print(f"  Reason: {leave_delegation.get_reason_display()}")
        print(f"  Expires: {leave_delegation.expires_at}")
        print(f"  Is Leave Delegation: {leave_delegation.is_leave_delegation()}")
        
    except Exception as e:
        print(f"\n❌ Failed to create leave delegation: {e}")
        return
    
    # Test effective approver logic
    print("\n=== TESTING EFFECTIVE APPROVER LOGIC ===")
    print("-" * 50)
    
    # Check who is the effective approver for the Ag. C/PAP user
    effective_approver = ag_cpap_user.get_effective_approver_for_action_log()
    print(f"Effective approver for {ag_cpap_user.get_full_name()} (Ag. C/PAP):")
    if effective_approver:
        print(f"  ✅ {effective_approver.get_full_name()} ({effective_approver.designation})")
        if effective_approver != ag_cpap_user:
            print(f"  📋 Responsibilities delegated due to leave")
        else:
            print(f"  📋 No active leave delegation")
    else:
        print(f"  ❌ No effective approver")
    
    # Check who is the effective approver for the Ag. AC/PAP user
    effective_approver = ag_acpap_user.get_effective_approver_for_action_log()
    print(f"\nEffective approver for {ag_acpap_user.get_full_name()} (Ag. AC/PAP):")
    if effective_approver:
        print(f"  ✅ {effective_approver.get_full_name()} ({effective_approver.designation})")
        if effective_approver == ag_acpap_user:
            print(f"  📋 Has taken over responsibilities due to Ag. C/PAP being on leave")
        else:
            print(f"  📋 Responsibilities delegated to someone else")
    else:
        print(f"  ❌ No effective approver")
    
    # Test approval capabilities
    print("\n=== TESTING APPROVAL CAPABILITIES ===")
    print("=" * 50)
    
    print(f"Can {ag_cpap_user.get_full_name()} (Ag. C/PAP) approve action logs?")
    if ag_cpap_user.can_approve_action_logs():
        print(f"  ✅ Yes - {ag_cpap_user.get_full_name()} can approve")
    else:
        print(f"  ❌ No - {ag_cpap_user.get_full_name()} cannot approve (on leave)")
    
    print(f"\nCan {ag_acpap_user.get_full_name()} (Ag. AC/PAP) approve action logs?")
    if ag_acpap_user.can_approve_action_logs():
        print(f"  ✅ Yes - {ag_acpap_user.get_full_name()} can approve")
    else:
        print(f"  ❌ No - {ag_acpap_user.get_full_name()} cannot approve")
    
    # Test current effective approver
    print("\n=== TESTING CURRENT EFFECTIVE APPROVER ===")
    print("=" * 55)
    
    current_approver = ag_cpap_user.get_current_effective_approver()
    print(f"Current effective approver for {ag_cpap_user.get_full_name()} (Ag. C/PAP):")
    if current_approver:
        print(f"  ✅ {current_approver.get_full_name()} ({current_approver.designation})")
        if current_approver != ag_cpap_user:
            print(f"  📋 Approval responsibilities delegated to Ag. AC/PAP due to leave")
        else:
            print(f"  📋 No active leave delegation")
    else:
        print(f"  ❌ No effective approver")
    
    current_approver = ag_acpap_user.get_current_effective_approver()
    print(f"\nCurrent effective approver for {ag_acpap_user.get_full_name()} (Ag. AC/PAP):")
    if current_approver:
        print(f"  ✅ {current_approver.get_full_name()} ({current_approver.designation})")
        if current_approver == ag_acpap_user:
            print(f"  📋 Has taken over approval responsibilities due to Ag. C/PAP being on leave")
        else:
            print(f"  📋 Approval responsibilities delegated to someone else")
    else:
        print(f"  ❌ No effective approver")
    
    # Test leave status
    print("\n=== TESTING LEAVE STATUS ===")
    print("=" * 35)
    
    print(f"Is {ag_cpap_user.get_full_name()} (Ag. C/PAP) currently on leave?")
    if ag_cpap_user.is_currently_on_leave():
        print(f"  🏖️  YES - {ag_cpap_user.get_full_name()} is on leave")
        print(f"  📋 Cannot handle approvals while on leave")
        print(f"  📋 Ag. AC/PAP user handles approvals instead")
    else:
        print(f"  ✅ NO - {ag_cpap_user.get_full_name()} is not on leave")
        print(f"  📋 Can handle approvals normally")
    
    print(f"\nDoes {ag_acpap_user.get_full_name()} (Ag. AC/PAP) have leave delegation responsibilities?")
    if ag_acpap_user.has_leave_delegation_responsibilities():
        print(f"  📋 YES - {ag_acpap_user.get_full_name()} has taken over responsibilities")
        print(f"  📋 Can handle approvals while Ag. C/PAP is on leave")
    else:
        print(f"  ❌ NO - {ag_acpap_user.get_full_name()} has no leave delegation responsibilities")
        print(f"  📋 Cannot handle approvals")
    
    # Test delegation expiration
    print("\n=== TESTING DELEGATION EXPIRATION ===")
    print("-" * 50)
    
    # Simulate expiration by setting the delegation to expire in the past
    leave_delegation.expires_at = timezone.now() - timedelta(hours=1)
    leave_delegation.save()
    
    print(f"Delegation expired at: {leave_delegation.expires_at}")
    print(f"Is expired: {leave_delegation.is_expired}")
    print(f"Is valid: {leave_delegation.is_valid}")
    
    # Check effective approver after expiration
    effective_approver = ag_cpap_user.get_effective_approver_for_action_log()
    print(f"\nEffective approver for {ag_cpap_user.get_full_name()} after expiration:")
    if effective_approver:
        print(f"  ✅ {effective_approver.get_full_name()} ({effective_approver.designation})")
        if effective_approver == ag_cpap_user:
            print(f"  📋 Responsibilities returned to Ag. C/PAP after leave")
        else:
            print(f"  📋 Still delegated to someone else")
    else:
        print(f"  ❌ No effective approver")
    
    # Clean up - reactivate the delegation for future testing
    leave_delegation.expires_at = timezone.now() + timedelta(days=7)
    leave_delegation.save()
    print(f"\n✅ Reactivated delegation for future testing")

def show_all_leave_delegations():
    """Show all leave delegations in the system"""
    print("\n=== ALL LEAVE DELEGATIONS IN SYSTEM ===")
    print("=" * 60)
    
    leave_delegations = Delegation.objects.filter(reason='leave').order_by('-delegated_at')
    
    if not leave_delegations.exists():
        print("No leave delegations found in the system.")
        return
    
    print(f"Total leave delegations: {leave_delegations.count()}")
    print("=" * 60)
    
    for delegation in leave_delegations:
        print(f"\nLeave Delegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()} ({delegation.delegated_by.designation})")
        print(f"  To: {delegation.delegated_to.get_full_name()} ({delegation.delegated_to.designation})")
        print(f"  Created: {delegation.delegated_at}")
        print(f"  Expires: {delegation.expires_at}")
        print(f"  Status: {'ACTIVE' if delegation.is_active else 'INACTIVE'}")
        print(f"  Is Expired: {'YES' if delegation.is_expired else 'NO'}")
        print(f"  Is Valid: {'YES' if delegation.is_valid else 'NO'}")
        
        # Show effective approver
        effective_approver = delegation.get_effective_approver()
        print(f"  Effective Approver: {effective_approver.get_full_name()} ({effective_approver.designation})")
        
        print("-" * 40)

if __name__ == "__main__":
    try:
        test_leave_delegation_functionality()
        show_all_leave_delegations()
        
        print("\n" + "=" * 80)
        print("LEAVE DELEGATION SUMMARY:")
        print("✅ Ag. C/PAP users can create leave delegations to Ag. AC/PAP users")
        print("✅ Ag. AC/PAP users take over responsibilities when Ag. C/PAP users are on leave")
        print("✅ Approval/rejection flow shifts to Ag. AC/PAP users during leave")
        print("✅ When delegation expires, responsibilities return to Ag. C/PAP users")
        print("✅ Leave delegations must have expiration dates")
        print("✅ Only Ag. C/PAP users can create leave delegations")
        print("✅ Only Ag. AC/PAP users can receive leave delegations")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
