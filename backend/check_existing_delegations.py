#!/usr/bin/env python3
"""
Script to check existing delegations and clean them up for testing.
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

def check_delegations():
    """Check all existing delegations"""
    print("=== CHECKING EXISTING DELEGATIONS ===")
    print("=" * 50)
    
    delegations = Delegation.objects.all()
    print(f"Total delegations: {delegations.count()}")
    
    for delegation in delegations:
        print(f"\nDelegation ID: {delegation.id}")
        print(f"  From: {delegation.delegated_by.get_full_name()} ({delegation.delegated_by.designation})")
        print(f"  To: {delegation.delegated_to.get_full_name()} ({delegation.delegated_to.designation})")
        print(f"  Reason: {delegation.reason}")
        print(f"  Active: {delegation.is_active}")
        print(f"  Expires: {delegation.expires_at}")
        print(f"  Created: {delegation.delegated_at}")

def clean_delegations():
    """Clean up all delegations for testing"""
    print(f"\n=== CLEANING UP DELEGATIONS ===")
    print("=" * 50)
    
    delegations = Delegation.objects.all()
    count = delegations.count()
    
    if count > 0:
        delegations.delete()
        print(f"Deleted {count} delegations")
    else:
        print("No delegations to delete")

if __name__ == "__main__":
    check_delegations()
    
    response = input("\nDo you want to clean up all delegations? (y/N): ")
    if response.lower() == 'y':
        clean_delegations()
        print("Delegations cleaned up successfully!")
    else:
        print("No changes made.")

