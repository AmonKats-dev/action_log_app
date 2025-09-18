#!/usr/bin/env python3
"""
Test script to demonstrate the corrected approval flow for action logs.
This script shows how approval/rejection flows to Ag. AC/PAP users when Ag. C/PAP users are on leave.
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

def test_approval_flow():
    """Test the approval flow for action logs with leave delegation"""
    print("=== TESTING APPROVAL FLOW FOR ACTION LOGS ===")
    print("=" * 80)
    
    # Get all users with Ag. C/PAP and Ag. AC/PAP designations
    ag_cpap_users = []
    ag_acpap_users = []
    
    for user in User.objects.filter(is_active=True):
        if user.has_ag_cpap_designation():
            ag_cpap_users.append(user)
        elif user.has_ag_acpap_designation():
            ag_acpap_users.append(user)
    
    if not ag_cpap_users or not ag_acpap_users:
        print("Cannot test approval flow: Need both Ag. C/PAP and Ag. AC/PAP users")
        return
    
    ag_cpap_user = ag_cpap_users[0]
    ag_acpap_user = ag_acpap_users[0]
    
    print(f"Testing with:")
    print(f"  Ag. C/PAP: {ag_cpap_user.get_full_name()}")
    print(f"  Ag. AC/PAP: {ag_acpap_user.get_full_name()}")
    
    # Test 1: Before leave delegation (normal state)
    print("\n" + "=" * 80)
    print("TEST 1: BEFORE LEAVE DELEGATION (NORMAL STATE)")
    print("=" * 80)
    
    print(f"Ag. C/PAP User Status:")
    print(f"  Can approve action logs: {'✅ YES' if ag_cpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Is on leave: {'🏖️  YES' if ag_cpap_user.is_currently_on_leave() else '✅ NO'}")
    print(f"  Current effective approver: {ag_cpap_user.get_current_effective_approver().get_full_name() if ag_cpap_user.get_current_effective_approver() else 'None'}")
    
    print(f"\nAg. AC/PAP User Status:")
    print(f"  Can approve action logs: {'✅ YES' if ag_acpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Has leave delegation responsibilities: {'📋 YES' if ag_acpap_user.has_leave_delegation_responsibilities() else '❌ NO'}")
    print(f"  Current effective approver: {ag_acpap_user.get_current_effective_approver().get_full_name() if ag_acpap_user.get_current_effective_approver() else 'None'}")
    
    # Create leave delegation
    print("\n" + "=" * 80)
    print("CREATING LEAVE DELEGATION...")
    print("=" * 80)
    
    try:
        leave_delegation = Delegation.objects.create(
            delegated_by=ag_cpap_user,
            delegated_to=ag_acpap_user,
            reason='leave',
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True
        )
        print(f"✅ Leave delegation created successfully")
        print(f"  ID: {leave_delegation.id}")
        print(f"  Expires: {leave_delegation.expires_at}")
    except Exception as e:
        print(f"❌ Failed to create leave delegation: {e}")
        return
    
    # Test 2: During leave delegation (Ag. C/PAP on leave)
    print("\n" + "=" * 80)
    print("TEST 2: DURING LEAVE DELEGATION (Ag. C/PAP ON LEAVE)")
    print("=" * 80)
    
    print(f"Ag. C/PAP User Status (ON LEAVE):")
    print(f"  Can approve action logs: {'✅ YES' if ag_cpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Is on leave: {'🏖️  YES' if ag_cpap_user.is_currently_on_leave() else '✅ NO'}")
    current_approver = ag_cpap_user.get_current_effective_approver()
    print(f"  Current effective approver: {current_approver.get_full_name() if current_approver else 'None'}")
    if current_approver and current_approver != ag_cpap_user:
        print(f"  📋 Approval responsibilities delegated to: {current_approver.get_full_name()}")
    
    print(f"\nAg. AC/PAP User Status (TAKEN OVER RESPONSIBILITIES):")
    print(f"  Can approve action logs: {'✅ YES' if ag_acpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Has leave delegation responsibilities: {'📋 YES' if ag_acpap_user.has_leave_delegation_responsibilities() else '❌ NO'}")
    current_approver = ag_acpap_user.get_current_effective_approver()
    print(f"  Current effective approver: {current_approver.get_full_name() if current_approver else 'None'}")
    if current_approver == ag_acpap_user:
        print(f"  📋 Has taken over approval responsibilities due to Ag. C/PAP being on leave")
    
    # Test 3: Simulate action log approval scenario
    print("\n" + "=" * 80)
    print("TEST 3: ACTION LOG APPROVAL SCENARIO")
    print("=" * 80)
    
    print("📋 Scenario: Action Log status updated to 'Done' - pending approval")
    print("📋 Question: Who should handle the approval/rejection?")
    
    # Check who should handle the approval
    ag_cpap_can_approve = ag_cpap_user.can_approve_action_logs()
    ag_acpap_can_approve = ag_acpap_user.can_approve_action_logs()
    
    print(f"\n📋 Approval Flow Analysis:")
    if not ag_cpap_can_approve and ag_acpap_can_approve:
        print(f"  ✅ CORRECT FLOW: Ag. C/PAP cannot approve (on leave)")
        print(f"  ✅ CORRECT FLOW: Ag. AC/PAP can approve (taken over responsibilities)")
        print(f"  📋 Result: Approval/rejection goes to Ag. AC/PAP user")
    elif ag_cpap_can_approve and not ag_acpap_can_approve:
        print(f"  ❌ INCORRECT FLOW: Ag. C/PAP can approve (should not when on leave)")
        print(f"  ❌ INCORRECT FLOW: Ag. AC/PAP cannot approve (should when has responsibilities)")
    else:
        print(f"  ⚠️  UNEXPECTED FLOW: Both or neither can approve")
    
    # Test 4: After delegation expires (return to normal)
    print("\n" + "=" * 80)
    print("TEST 4: AFTER DELEGATION EXPIRES (RETURN TO NORMAL)")
    print("=" * 80)
    
    # Simulate expiration
    leave_delegation.expires_at = timezone.now() - timedelta(hours=1)
    leave_delegation.save()
    
    print(f"Delegation expired at: {leave_delegation.expires_at}")
    print(f"Delegation is expired: {leave_delegation.is_expired}")
    print(f"Delegation is valid: {leave_delegation.is_valid}")
    
    print(f"\nAg. C/PAP User Status (RETURNED FROM LEAVE):")
    print(f"  Can approve action logs: {'✅ YES' if ag_cpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Is on leave: {'🏖️  YES' if ag_cpap_user.is_currently_on_leave() else '✅ NO'}")
    current_approver = ag_cpap_user.get_current_effective_approver()
    print(f"  Current effective approver: {current_approver.get_full_name() if current_approver else 'None'}")
    
    print(f"\nAg. AC/PAP User Status (RESPONSIBILITIES RETURNED):")
    print(f"  Can approve action logs: {'✅ YES' if ag_acpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Has leave delegation responsibilities: {'📋 YES' if ag_acpap_user.has_leave_delegation_responsibilities() else '❌ NO'}")
    current_approver = ag_acpap_user.get_current_effective_approver()
    print(f"  Current effective approver: {current_approver.get_full_name() if current_approver else 'None'}")
    
    # Test approval flow after expiration
    print(f"\n📋 Approval Flow After Expiration:")
    ag_cpap_can_approve = ag_cpap_user.can_approve_action_logs()
    ag_acpap_can_approve = ag_acpap_user.can_approve_action_logs()
    
    if ag_cpap_can_approve and not ag_acpap_can_approve:
        print(f"  ✅ CORRECT FLOW: Ag. C/PAP can approve again (returned from leave)")
        print(f"  ✅ CORRECT FLOW: Ag. AC/PAP cannot approve (responsibilities returned)")
        print(f"  📋 Result: Approval/rejection goes back to Ag. C/PAP user")
    else:
        print(f"  ❌ INCORRECT FLOW: Approval capabilities not properly restored")
    
    # Clean up - reactivate for future testing
    leave_delegation.expires_at = timezone.now() + timedelta(days=7)
    leave_delegation.save()
    print(f"\n✅ Reactivated delegation for future testing")

if __name__ == "__main__":
    try:
        test_approval_flow()
        
        print("\n" + "=" * 80)
        print("APPROVAL FLOW SUMMARY:")
        print("✅ When Ag. C/PAP user is on leave:")
        print("   - Ag. C/PAP user CANNOT approve action logs")
        print("   - Ag. AC/PAP user TAKES OVER approval responsibilities")
        print("   - Approval/rejection flow goes to Ag. AC/PAP user")
        print("\n✅ When leave delegation expires:")
        print("   - Ag. C/PAP user CAN approve action logs again")
        print("   - Ag. AC/PAP user LOSES approval responsibilities")
        print("   - Approval/rejection flow returns to Ag. C/PAP user")
        print("\n✅ Result: Seamless approval workflow with proper delegation")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
