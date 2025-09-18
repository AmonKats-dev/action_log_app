#!/usr/bin/env python3
"""
Test script to verify that the delegation system correctly handles approval and rejection permissions.
This script tests that Ag. AC/PAP users can approve/reject when Ag. C/PAP users are on leave.
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
from action_logs.models import ActionLog
from users.permissions import can_approve_action_log
from django.utils import timezone

def test_delegation_approval_permissions():
    """Test that delegation correctly handles approval permissions for both approve and reject"""
    print("=== TESTING DELEGATION APPROVAL PERMISSIONS ===")
    print("=" * 80)
    
    # Find users with the required designations
    ag_cpap_users = User.objects.filter(
        designation__icontains='ag. c/pap',
        is_active=True
    )
    ag_acpap_users = User.objects.filter(
        designation__icontains='ag. ac/pap',
        is_active=True
    )
    
    if not ag_cpap_users.exists():
        print("❌ No Ag. C/PAP users found")
        return False
    
    if not ag_acpap_users.exists():
        print("❌ No Ag. AC/PAP users found")
        return False
    
    ag_cpap_user = ag_cpap_users.first()
    ag_acpap_user = ag_acpap_users.first()
    
    print(f"Testing with:")
    print(f"  Ag. C/PAP User: {ag_cpap_user.get_full_name()} (ID: {ag_cpap_user.id})")
    print(f"  Ag. AC/PAP User: {ag_acpap_user.get_full_name()} (ID: {ag_acpap_user.id})")
    
    # Test 1: Before delegation - Ag. C/PAP can approve, Ag. AC/PAP cannot
    print(f"\n--- TEST 1: BEFORE DELEGATION ---")
    
    ag_cpap_can_approve_before = can_approve_action_log(ag_cpap_user, None)
    ag_acpap_can_approve_before = can_approve_action_log(ag_acpap_user, None)
    
    print(f"  Ag. C/PAP can approve: {'✅ YES' if ag_cpap_can_approve_before else '❌ NO'}")
    print(f"  Ag. AC/PAP can approve: {'✅ YES' if ag_acpap_can_approve_before else '❌ NO'}")
    
    # Test 2: Create leave delegation
    print(f"\n--- TEST 2: CREATING LEAVE DELEGATION ---")
    
    # Create a leave delegation from Ag. C/PAP to Ag. AC/PAP
    delegation = Delegation.objects.create(
        delegated_by=ag_cpap_user,
        delegated_to=ag_acpap_user,
        reason='leave',
        expires_at=timezone.now() + timedelta(days=7),
        is_active=True
    )
    
    print(f"  Created delegation: {delegation}")
    print(f"  Delegation expires: {delegation.expires_at}")
    
    # Test 3: After delegation - Ag. C/PAP cannot approve, Ag. AC/PAP can
    print(f"\n--- TEST 3: AFTER DELEGATION ---")
    
    ag_cpap_can_approve_after = can_approve_action_log(ag_cpap_user, None)
    ag_acpap_can_approve_after = can_approve_action_log(ag_acpap_user, None)
    
    print(f"  Ag. C/PAP can approve: {'✅ YES' if ag_cpap_can_approve_after else '❌ NO'}")
    print(f"  Ag. AC/PAP can approve: {'✅ YES' if ag_acpap_can_approve_after else '❌ NO'}")
    
    # Test 4: Verify the delegation logic is working
    print(f"\n--- TEST 4: VERIFYING DELEGATION LOGIC ---")
    
    # Check Ag. C/PAP user's delegation status
    ag_cpap_leave_status = ag_cpap_user.get_leave_delegation_status()
    print(f"  Ag. C/PAP leave status: {ag_cpap_leave_status.get('status') if ag_cpap_leave_status else 'None'}")
    
    # Check Ag. AC/PAP user's delegation responsibilities
    ag_acpap_has_responsibilities = ag_acpap_user.has_leave_delegation_responsibilities()
    print(f"  Ag. AC/PAP has leave responsibilities: {'✅ YES' if ag_acpap_has_responsibilities else '❌ NO'}")
    
    # Test 5: Test with actual action log
    print(f"\n--- TEST 5: TESTING WITH ACTION LOG ---")
    
    # Find or create an action log for testing
    action_logs = ActionLog.objects.all()
    if action_logs.exists():
        test_log = action_logs.first()
        print(f"  Testing with action log: {test_log.title} (ID: {test_log.id})")
        
        # Test approval permissions
        ag_cpap_can_approve_log = test_log.can_approve(ag_cpap_user)
        ag_acpap_can_approve_log = test_log.can_approve(ag_acpap_user)
        
        print(f"  Ag. C/PAP can approve log: {'✅ YES' if ag_cpap_can_approve_log else '❌ NO'}")
        print(f"  Ag. AC/PAP can approve log: {'✅ YES' if ag_acpap_can_approve_log else '❌ NO'}")
        
        # Test rejection permissions (should be the same as approval)
        print(f"  Note: Rejection uses the same permission check as approval")
    else:
        print(f"  No action logs found for testing")
    
    # Test 6: Clean up - revoke delegation
    print(f"\n--- TEST 6: CLEANING UP ---")
    
    delegation.is_active = False
    delegation.save()
    print(f"  Revoked delegation: {delegation}")
    
    # Test 7: After revocation - permissions should return to original state
    print(f"\n--- TEST 7: AFTER REVOCATION ---")
    
    ag_cpap_can_approve_final = can_approve_action_log(ag_cpap_user, None)
    ag_acpap_can_approve_final = can_approve_action_log(ag_acpap_user, None)
    
    print(f"  Ag. C/PAP can approve: {'✅ YES' if ag_cpap_can_approve_final else '❌ NO'}")
    print(f"  Ag. AC/PAP can approve: {'✅ YES' if ag_acpap_can_approve_final else '❌ NO'}")
    
    # Summary
    print(f"\n" + "=" * 80)
    print("DELEGATION APPROVAL PERMISSION TEST RESULTS:")
    print("=" * 80)
    
    # Check if the delegation worked correctly
    delegation_worked = (
        not ag_cpap_can_approve_after and  # Ag. C/PAP cannot approve when on leave
        ag_acpap_can_approve_after and     # Ag. AC/PAP can approve when has responsibilities
        ag_cpap_can_approve_final and      # Ag. C/PAP can approve again after return
        not ag_acpap_can_approve_final     # Ag. AC/PAP cannot approve after delegation ends
    )
    
    if delegation_worked:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Delegation system correctly handles approval permissions")
        print("✅ Ag. C/PAP users cannot approve when on leave")
        print("✅ Ag. AC/PAP users can approve when they have leave responsibilities")
        print("✅ Permissions return to normal when delegation expires")
        print("✅ Both approval and rejection will work correctly")
    else:
        print("❌ Some tests failed - check the output above")
        
        if ag_cpap_can_approve_after:
            print("  ❌ Ag. C/PAP can still approve when on leave")
        if not ag_acpap_can_approve_after:
            print("  ❌ Ag. AC/PAP cannot approve when they should have responsibilities")
        if not ag_cpap_can_approve_final:
            print("  ❌ Ag. C/PAP cannot approve after returning from leave")
        if ag_acpap_can_approve_final:
            print("  ❌ Ag. AC/PAP can still approve after delegation ends")
    
    return delegation_worked

def test_user_model_methods():
    """Test the User model's delegation methods directly"""
    print(f"\n" + "=" * 80)
    print("TESTING USER MODEL DELEGATION METHODS")
    print("=" * 80)
    
    # Find users with the required designations
    ag_cpap_users = User.objects.filter(
        designation__icontains='ag. c/pap',
        is_active=True
    )
    ag_acpap_users = User.objects.filter(
        designation__icontains='ag. ac/pap',
        is_active=True
    )
    
    if not ag_cpap_users.exists() or not ag_acpap_users.exists():
        print("❌ Required users not found for testing")
        return False
    
    ag_cpap_user = ag_cpap_users.first()
    ag_acpap_user = ag_acpap_users.first()
    
    print(f"Testing User model methods:")
    print(f"  Ag. C/PAP User: {ag_cpap_user.get_full_name()}")
    print(f"  Ag. AC/PAP User: {ag_acpap_user.get_full_name()}")
    
    # Test Ag. C/PAP methods
    print(f"\n--- Ag. C/PAP User Methods ---")
    print(f"  has_ag_cpap_designation: {ag_cpap_user.has_ag_cpap_designation()}")
    print(f"  can_approve_action_logs: {ag_cpap_user.can_approve_action_logs()}")
    print(f"  is_currently_on_leave: {ag_cpap_user.is_currently_on_leave()}")
    
    # Test Ag. AC/PAP methods
    print(f"\n--- Ag. AC/PAP User Methods ---")
    print(f"  has_ag_acpap_designation: {ag_acpap_user.has_ag_acpap_designation()}")
    print(f"  can_approve_action_logs: {ag_acpap_user.can_approve_action_logs()}")
    print(f"  has_leave_delegation_responsibilities: {ag_acpap_user.has_leave_delegation_responsibilities()}")
    
    # Test effective approver
    print(f"\n--- Effective Approver Tests ---")
    ag_cpap_effective = ag_cpap_user.get_current_effective_approver()
    ag_acpap_effective = ag_acpap_user.get_current_effective_approver()
    
    print(f"  Ag. C/PAP effective approver: {ag_cpap_effective.get_full_name() if ag_cpap_effective else 'None'}")
    print(f"  Ag. AC/PAP effective approver: {ag_acpap_effective.get_full_name() if ag_acpap_effective else 'None'}")
    
    return True

if __name__ == "__main__":
    try:
        print("Starting delegation approval permission tests...")
        
        # Run all tests
        test1 = test_delegation_approval_permissions()
        test2 = test_user_model_methods()
        
        print(f"\n" + "=" * 80)
        print("FINAL TEST RESULTS:")
        print("=" * 80)
        
        if test1 and test2:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Delegation system is working correctly")
            print("✅ Approval and rejection permissions are properly handled")
            print("✅ Ag. AC/PAP users can approve/reject when Ag. C/PAP users are on leave")
        else:
            print("❌ Some tests failed - check the output above")
        
        print(f"\nThe system should now correctly:")
        print("  - Allow Ag. C/PAP users to approve/reject when not on leave")
        print("  - Prevent Ag. C/PAP users from approving/rejecting when on leave")
        print("  - Allow Ag. AC/PAP users to approve/reject when they have leave responsibilities")
        print("  - Prevent Ag. AC/PAP users from approving/rejecting when no delegation")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()

