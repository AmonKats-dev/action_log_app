#!/usr/bin/env python3
"""
Simple script to test and display delegation data from the backend.
This script can be run to view all delegations in the system.
"""

import os
import sys
import django
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Delegation, User
from django.utils import timezone

def list_all_delegations():
    """List all delegations in the system"""
    print("=== DELEGATION TABLE LIST ===")
    print("=" * 80)
    
    # Get all delegations
    delegations = Delegation.objects.all().order_by('-delegated_at')
    
    if not delegations.exists():
        print("No delegations found in the system.")
        return
    
    print(f"Total delegations found: {delegations.count()}")
    print("=" * 80)
    
    for delegation in delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Reason: {delegation.get_reason_display()}")
        print(f"  Created: {delegation.delegated_at}")
        print(f"  Expires: {delegation.expires_at or 'No expiration'}")
        print(f"  Status: {'ACTIVE' if delegation.is_active else 'INACTIVE'}")
        print(f"  Expired: {'YES' if delegation.is_expired else 'NO'}")
        print(f"  Valid: {'YES' if delegation.is_valid else 'NO'}")
        
        # Show leave delegation specific information
        if delegation.reason == 'leave':
            print(f"  🏖️  LEAVE DELEGATION - Ag. AC/PAP takes over responsibilities")
            effective_approver = delegation.get_effective_approver()
            print(f"  Effective Approver: {effective_approver.get_full_name()}")
            
            # Show approval flow information
            if delegation.is_active and not delegation.is_expired:
                print(f"  📋 Approval Flow: Goes to Ag. AC/PAP user (Ag. C/PAP on leave)")
                print(f"  📋 Ag. C/PAP user cannot approve while on leave")
            else:
                print(f"  📋 Approval Flow: Returned to Ag. C/PAP user (delegation expired)")
                print(f"  📋 Ag. C/PAP user can approve again")
        
        if delegation.reason:
            print(f"  Reason: {delegation.reason}")
        
        if delegation.expires_at:
            time_until_expiry = delegation.expires_at - timezone.now()
            if time_until_expiry.total_seconds() > 0:
                print(f"  Time until expiry: {time_until_expiry}")
            else:
                print(f"  EXPIRED: {abs(time_until_expiry)} ago")
        
        print("-" * 40)

def list_active_delegations():
    """List only active delegations"""
    print("\n=== ACTIVE DELEGATIONS ONLY ===")
    print("=" * 50)
    
    active_delegations = Delegation.objects.filter(is_active=True).order_by('-delegated_at')
    
    if not active_delegations.exists():
        print("No active delegations found.")
        return
    
    print(f"Active delegations: {active_delegations.count()}")
    print("=" * 50)
    
    for delegation in active_delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Expires: {delegation.expires_at or 'No expiration'}")
        print(f"  Valid: {'YES' if delegation.is_valid else 'NO'}")

def list_expired_delegations():
    """List only expired delegations"""
    print("\n=== EXPIRED DELEGATIONS ONLY ===")
    print("=" * 50)
    
    expired_delegations = Delegation.objects.filter(
        expires_at__lt=timezone.now()
    ).order_by('-expires_at')
    
    if not expired_delegations.exists():
        print("No expired delegations found.")
        return
    
    print(f"Expired delegations: {expired_delegations.count()}")
    print("=" * 50)
    
    for delegation in expired_delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Expired: {delegation.expires_at}")
        print(f"  Status: {'ACTIVE' if delegation.is_active else 'INACTIVE'}")

def show_summary():
    """Show summary statistics"""
    print("\n=== SUMMARY STATISTICS ===")
    print("=" * 30)
    
    total = Delegation.objects.count()
    active = Delegation.objects.filter(is_active=True).count()
    expired = Delegation.objects.filter(expires_at__lt=timezone.now()).count()
    valid = Delegation.objects.filter(is_active=True, expires_at__gt=timezone.now()).count()
    
    print(f"Total delegations: {total}")
    print(f"Active delegations: {active}")
    print(f"Expired delegations: {expired}")
    print(f"Valid delegations: {valid}")

if __name__ == "__main__":
    try:
        list_all_delegations()
        list_active_delegations()
        list_expired_delegations()
        show_summary()
        
        print("\n" + "=" * 80)
        print("To access delegations via API:")
        print("  GET /api/users/delegations/ - List all delegations")
        print("  GET /api/users/delegations/my_delegations/ - Get user's delegations")
        print("  POST /api/users/delegations/{id}/revoke/ - Revoke a delegation")
        print("\nTo access via Django Admin:")
        print("  http://localhost:8000/admin/ - Navigate to Users > Delegations")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
