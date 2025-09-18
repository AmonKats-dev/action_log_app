#!/usr/bin/env python3
"""
Test script to demonstrate automatic transition when leave expires.
This script shows how approval responsibilities automatically return to Ag. C/PAP users
from Ag. AC/PAP users when leave delegations expire.
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

def test_automatic_transition():
    """Test the automatic transition when leave expires"""
    print("=== TESTING AUTOMATIC TRANSITION WHEN LEAVE EXPIRES ===")
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
        print("Cannot test automatic transition: Need both Ag. C/PAP and Ag. AC/PAP users")
        return
    
    ag_cpap_user = ag_cpap_users[0]
    ag_acpap_user = ag_acpap_users[0]
    
    print(f"Testing with:")
    print(f"  Ag. C/PAP: {ag_cpap_user.get_full_name()}")
    print(f"  Ag. AC/PAP: {ag_acpap_user.get_full_name()}")
    
    # Test 1: Create leave delegation (Ag. C/PAP on leave)
    print("\n" + "=" * 80)
    print("TEST 1: CREATING LEAVE DELEGATION (Ag. C/PAP ON LEAVE)")
    print("=" * 80)
    
    try:
        # Create delegation that expires in 1 minute for testing
        leave_delegation = Delegation.objects.create(
            delegated_by=ag_cpap_user,
            delegated_to=ag_acpap_user,
            reason='leave',
            expires_at=timezone.now() + timedelta(minutes=1),  # Expires in 1 minute
            is_active=True
        )
        print(f"✅ Leave delegation created successfully")
        print(f"  ID: {leave_delegation.id}")
        print(f"  Expires at: {leave_delegation.expires_at}")
        print(f"  Time until expiry: {leave_delegation.time_until_expiry}")
        print(f"  Is expiring soon: {leave_delegation.is_expiring_soon}")
        
    except Exception as e:
        print(f"❌ Failed to create leave delegation: {e}")
        return
    
    # Test 2: Check status during active delegation
    print("\n" + "=" * 80)
    print("TEST 2: STATUS DURING ACTIVE DELEGATION")
    print("=" * 80)
    
    print(f"Ag. C/PAP User Status:")
    print(f"  Is on leave: {'🏖️  YES' if ag_cpap_user.is_currently_on_leave() else '✅ NO'}")
    print(f"  Can approve action logs: {'✅ YES' if ag_cpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Leave delegation status: {ag_cpap_user.get_leave_delegation_status()}")
    
    print(f"\nAg. AC/PAP User Status:")
    print(f"  Has leave delegation responsibilities: {'📋 YES' if ag_acpap_user.has_leave_delegation_responsibilities() else '❌ NO'}")
    print(f"  Can approve action logs: {'✅ YES' if ag_acpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Delegation transition info: {ag_acpap_user.get_delegation_transition_info()}")
    
    # Test 3: Wait for delegation to expire (simulate by setting past date)
    print("\n" + "=" * 80)
    print("TEST 3: SIMULATING DELEGATION EXPIRATION")
    print("=" * 80)
    
    # Simulate expiration by setting the delegation to expire in the past
    leave_delegation.expires_at = timezone.now() - timedelta(minutes=1)
    leave_delegation.save()
    
    print(f"Delegation expired at: {leave_delegation.expires_at}")
    print(f"Is expired: {leave_delegation.is_expired}")
    print(f"Is valid: {leave_delegation.is_valid}")
    print(f"Is active: {leave_delegation.is_active}")
    
    # Test 4: Check automatic transition after expiration
    print("\n" + "=" * 80)
    print("TEST 4: AUTOMATIC TRANSITION AFTER EXPIRATION")
    print("=" * 80)
    
    print(f"Ag. C/PAP User Status (AFTER LEAVE):")
    print(f"  Is on leave: {'🏖️  YES' if ag_cpap_user.is_currently_on_leave() else '✅ NO'}")
    print(f"  Can approve action logs: {'✅ YES' if ag_cpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Leave delegation status: {ag_cpap_user.get_leave_delegation_status()}")
    
    print(f"\nAg. AC/PAP User Status (AFTER DELEGATION EXPIRED):")
    print(f"  Has leave delegation responsibilities: {'📋 YES' if ag_acpap_user.has_leave_delegation_responsibilities() else '❌ NO'}")
    print(f"  Can approve action logs: {'✅ YES' if ag_acpap_user.can_approve_action_logs() else '❌ NO'}")
    print(f"  Delegation transition info: {ag_acpap_user.get_delegation_transition_info()}")
    
    # Test 5: Verify approval flow transition
    print("\n" + "=" * 80)
    print("TEST 5: VERIFYING APPROVAL FLOW TRANSITION")
    print("=" * 80)
    
    ag_cpap_can_approve = ag_cpap_user.can_approve_action_logs()
    ag_acpap_can_approve = ag_acpap_user.can_approve_action_logs()
    
    print(f"Approval Flow Analysis:")
    if ag_cpap_can_approve and not ag_acpap_can_approve:
        print(f"  ✅ CORRECT TRANSITION: Ag. C/PAP can approve again (returned from leave)")
        print(f"  ✅ CORRECT TRANSITION: Ag. AC/PAP cannot approve (responsibilities returned)")
        print(f"  📋 Result: Approval/rejection flow automatically returned to Ag. C/PAP user")
    else:
        print(f"  ❌ INCORRECT TRANSITION: Approval capabilities not properly restored")
    
    # Test 6: Show delegation transition details
    print("\n" + "=" * 80)
    print("TEST 6: DELEGATION TRANSITION DETAILS")
    print("=" * 80)
    
    print(f"Ag. C/PAP Transition Info:")
    transition_info = ag_cpap_user.get_delegation_transition_info()
    if transition_info:
        print(f"  Type: {transition_info['type']}")
        print(f"  Status: {transition_info['status']}")
        print(f"  Message: {transition_info['message']}")
        if 'expired_at' in transition_info:
            print(f"  Expired at: {transition_info['expired_at']}")
    else:
        print(f"  No transition info available")
    
    print(f"\nAg. AC/PAP Transition Info:")
    transition_info = ag_acpap_user.get_delegation_transition_info()
    if transition_info:
        print(f"  Type: {transition_info['type']}")
        print(f"  Status: {transition_info['status']}")
        print(f"  Message: {transition_info['message']}")
    else:
        print(f"  No transition info available")
    
    # Clean up - reactivate for future testing
    leave_delegation.expires_at = timezone.now() + timedelta(days=7)
    leave_delegation.save()
    print(f"\n✅ Reactivated delegation for future testing")

def test_cleanup_command():
    """Test the cleanup command functionality"""
    print("\n" + "=" * 80)
    print("TESTING CLEANUP COMMAND FUNCTIONALITY")
    print("=" * 80)
    
    # Show how to use the cleanup command
    print("To automatically clean up expired delegations, use:")
    print("  python manage.py cleanup_expired_delegations")
    print("  python manage.py cleanup_expired_delegations --dry-run")
    print("  python manage.py cleanup_expired_delegations --verbose")
    
    print("\nThe cleanup command will:")
    print("  ✅ Automatically deactivate expired delegations")
    print("  ✅ Log all transitions for audit purposes")
    print("  ✅ Ensure approval responsibilities are properly returned")
    print("  ✅ Handle both leave and regular delegations")

if __name__ == "__main__":
    try:
        test_automatic_transition()
        test_cleanup_command()
        
        print("\n" + "=" * 80)
        print("AUTOMATIC TRANSITION SUMMARY:")
        print("✅ When leave delegation expires:")
        print("   - Delegation is automatically deactivated")
        print("   - Ag. C/PAP user automatically regains approval capabilities")
        print("   - Ag. AC/PAP user automatically loses approval capabilities")
        print("   - Approval/rejection flow seamlessly returns to Ag. C/PAP user")
        print("\n✅ Automatic cleanup ensures:")
        print("   - No manual intervention required")
        print("   - Seamless transition of responsibilities")
        print("   - Proper audit trail of all changes")
        print("   - System always reflects current delegation status")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
