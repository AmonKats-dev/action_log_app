#!/usr/bin/env python3
"""
Simple script to check current time and delegation expiration.
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Delegation
from django.utils import timezone

def check_time():
    """Check current time and delegation status"""
    print("=== CHECKING TIME AND DELEGATION STATUS ===")
    print("=" * 50)
    
    now = timezone.now()
    print(f"Current time (UTC): {now}")
    print(f"Current time (local): {now.astimezone()}")
    
    # Check delegations
    delegations = Delegation.objects.all()
    print(f"\nTotal delegations: {delegations.count()}")
    
    for delegation in delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()}")
        print(f"  To: {delegation.delegated_to.get_full_name()}")
        print(f"  Reason: {delegation.reason}")
        print(f"  Active: {delegation.is_active}")
        print(f"  Expires: {delegation.expires_at}")
        print(f"  Created: {delegation.delegated_at}")
        
        if delegation.expires_at:
            time_diff = delegation.expires_at - now
            print(f"  Time until expiry: {time_diff}")
            print(f"  Is expired: {delegation.is_expired}")
            print(f"  Is expiring soon: {delegation.is_expiring_soon}")
            
            # Check the logic in the save method
            if delegation.expires_at and now > delegation.expires_at:
                print(f"  ❌ EXPIRATION LOGIC: expires_at < now (should be inactive)")
            else:
                print(f"  ✅ EXPIRATION LOGIC: expires_at > now (should be active)")

if __name__ == "__main__":
    check_time()

