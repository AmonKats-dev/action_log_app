#!/usr/bin/env python3
"""
Test script to demonstrate automatic delegation expiration and revocation.
This script shows how delegations are automatically revoked when they expire
and when users log into the system.
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
from django.contrib.auth.signals import user_logged_in
from django.dispatch import Signal

def test_delegation_expiry():
    """Test the automatic delegation expiration functionality"""
    
    print("=== Testing Automatic Delegation Expiration ===\n")
    
    # Get all delegations
    delegations = Delegation.objects.all()
    print(f"Total delegations in system: {delegations.count()}")
    
    # Show active delegations
    active_delegations = delegations.filter(is_active=True)
    print(f"Active delegations: {active_delegations.count()}")
    
    for delegation in active_delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Created: {delegation.delegated_at}")
        print(f"  Expires: {delegation.expires_at}")
        print(f"  Is Active: {delegation.is_active}")
        print(f"  Is Expired: {delegation.is_expired}")
        print(f"  Is Valid: {delegation.is_valid}")
        
        if delegation.expires_at:
            time_until_expiry = delegation.expires_at - timezone.now()
            if time_until_expiry.total_seconds() > 0:
                print(f"  Time until expiry: {time_until_expiry}")
            else:
                print(f"  EXPIRED: {abs(time_until_expiry)} ago")
    
    # Test automatic revocation
    print("\n=== Testing Automatic Revocation ===")
    revoked_count = Delegation.revoke_expired_delegations()
    print(f"Automatically revoked {revoked_count} expired delegations")
    
    # Show updated status
    print("\n=== After Automatic Revocation ===")
    active_delegations = Delegation.objects.filter(is_active=True)
    print(f"Active delegations after revocation: {active_delegations.count()}")
    
    for delegation in active_delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Expires: {delegation.expires_at}")
        print(f"  Is Active: {delegation.is_active}")
        print(f"  Is Expired: {delegation.is_expired}")
        print(f"  Is Valid: {delegation.is_valid}")

def test_login_signal():
    """Test the automatic delegation check on user login"""
    
    print("\n=== Testing Login Signal Delegation Check ===")
    
    # Get a user to simulate login
    users = User.objects.filter(is_active=True)
    if not users.exists():
        print("No active users found to test login signal")
        return
    
    test_user = users.first()
    print(f"Testing with user: {test_user.get_full_name()} ({test_user.username})")
    
    # Simulate the login signal
    from users.signals import check_user_delegations_on_login
    
    # Create a mock request object
    class MockRequest:
        pass
    
    request = MockRequest()
    
    # Trigger the login signal manually
    print("Triggering login signal...")
    check_user_delegations_on_login(sender=User, user=test_user, request=request)
    
    print("Login signal test completed")

if __name__ == "__main__":
    try:
        test_delegation_expiry()
        test_login_signal()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
