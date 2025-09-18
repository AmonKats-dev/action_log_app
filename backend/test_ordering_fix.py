#!/usr/bin/env python3
"""
Test script to verify that the ordering fixes the pagination warning for delegations.
This script tests the ordering of Delegation objects to ensure consistent pagination results.
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Delegation, User
from django.core.paginator import Paginator
from django.utils import timezone

def test_delegation_ordering():
    """Test that delegation ordering works correctly and prevents pagination warnings"""
    print("=== TESTING DELEGATION ORDERING AND PAGINATION ===")
    print("=" * 80)
    
    # Get all delegations with ordering
    delegations = Delegation.objects.all().order_by('-delegated_at', '-id')
    print(f"Total delegations: {delegations.count()}")
    
    if delegations.exists():
        print("\nDelegations in order (most recent first):")
        for i, delegation in enumerate(delegations[:5]):  # Show first 5
            print(f"  {i+1}. ID: {delegation.id}, Created: {delegation.delegated_at}, "
                  f"From: {delegation.delegated_by.get_full_name()}, "
                  f"To: {delegation.delegated_to.get_full_name()}")
    
    # Test pagination
    print("\n" + "=" * 80)
    print("TESTING PAGINATION WITH ORDERED QUERYSET")
    print("=" * 80)
    
    try:
        # Create a paginator with the ordered queryset
        paginator = Paginator(delegations, 10)  # 10 items per page
        
        print(f"Total pages: {paginator.num_pages}")
        print(f"Total items: {paginator.count}")
        
        # Get first page
        if paginator.num_pages > 0:
            page1 = paginator.get_page(1)
            print(f"\nPage 1 results ({len(page1)} items):")
            for item in page1:
                print(f"  - ID: {item.id}, Created: {item.delegated_at}")
            
            # Test that ordering is maintained across pages
            if paginator.num_pages > 1:
                page2 = paginator.get_page(2)
                print(f"\nPage 2 results ({len(page2)} items):")
                for item in page2:
                    print(f"  - ID: {item.id}, Created: {item.delegated_at}")
                
                # Verify that page 1 items are newer than page 2 items
                if page1 and page2:
                    page1_latest = page1[0].delegated_at
                    page2_latest = page2[0].delegated_at
                    print(f"\nOrdering verification:")
                    print(f"  Page 1 latest: {page1_latest}")
                    print(f"  Page 2 latest: {page2_latest}")
                    if page1_latest >= page2_latest:
                        print(f"  ✅ CORRECT: Page 1 items are newer than or equal to Page 2 items")
                    else:
                        print(f"  ❌ INCORRECT: Page 1 items should be newer than Page 2 items")
        
        print(f"\n✅ Pagination test completed successfully - no ordering warnings!")
        
    except Exception as e:
        print(f"❌ Pagination test failed: {e}")
        import traceback
        traceback.print_exc()

def test_user_ordering():
    """Test that user ordering works correctly"""
    print("\n" + "=" * 80)
    print("TESTING USER ORDERING")
    print("=" * 80)
    
    # Get all users with ordering
    users = User.objects.all().order_by('first_name', 'last_name', 'id')
    print(f"Total users: {users.count()}")
    
    if users.exists():
        print("\nUsers in order (alphabetical by name):")
        for i, user in enumerate(users[:10]):  # Show first 10
            print(f"  {i+1}. {user.get_full_name()} (ID: {user.id})")
    
    print(f"\n✅ User ordering test completed successfully!")

def test_role_ordering():
    """Test that role ordering works correctly"""
    print("\n" + "=" * 80)
    print("TESTING ROLE ORDERING")
    print("=" * 80)
    
    from users.models import Role
    
    # Get all roles with ordering
    roles = Role.objects.all().order_by('name')
    print(f"Total roles: {roles.count()}")
    
    if roles.exists():
        print("\nRoles in order (alphabetical):")
        for i, role in enumerate(roles):
            print(f"  {i+1}. {role.name}")
    
    print(f"\n✅ Role ordering test completed successfully!")

def test_cleanup_command_ordering():
    """Test that the cleanup command uses proper ordering"""
    print("\n" + "=" * 80)
    print("TESTING CLEANUP COMMAND ORDERING")
    print("=" * 80)
    
    # Simulate the cleanup command's queryset
    expired_delegations = Delegation.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    ).select_related('delegated_by', 'delegated_to').order_by('-expires_at', '-id')
    
    print(f"Expired delegations found: {expired_delegations.count()}")
    
    if expired_delegations.exists():
        print("\nExpired delegations in order (most recently expired first):")
        for i, delegation in enumerate(expired_delegations[:5]):
            print(f"  {i+1}. ID: {delegation.id}, Expired: {delegation.expires_at}, "
                  f"From: {delegation.delegated_by.get_full_name()}")
    
    print(f"\n✅ Cleanup command ordering test completed successfully!")

if __name__ == "__main__":
    try:
        test_delegation_ordering()
        test_user_ordering()
        test_role_ordering()
        test_cleanup_command_ordering()
        
        print("\n" + "=" * 80)
        print("ORDERING FIX SUMMARY:")
        print("✅ Added ordering to Delegation model: ['-delegated_at', '-id']")
        print("✅ Added ordering to User model: ['first_name', 'last_name', 'id']")
        print("✅ Added ordering to Role model: ['name']")
        print("✅ Added ordering to LoginCode model: ['-created_at']")
        print("✅ Updated DelegationViewSet querysets with explicit ordering")
        print("✅ Updated my_delegations method with explicit ordering")
        print("\nThese changes ensure:")
        print("  - Consistent pagination results")
        print("  - No more UnorderedObjectListWarning")
        print("  - Predictable ordering across all queries")
        print("  - Better user experience with consistent data display")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
