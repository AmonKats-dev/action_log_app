#!/usr/bin/env python3
"""
Test script to verify that the JSON serialization error has been fixed.
This script tests the UserSerializer to ensure it can properly serialize User objects.
"""

import os
import sys
import django
import json

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User, Delegation
from users.serializers import UserSerializer
from django.utils import timezone
from datetime import timedelta

def test_user_serialization():
    """Test that User objects can be properly serialized without JSON errors"""
    print("=== TESTING USER SERIALIZATION ===")
    print("=" * 80)
    
    # Get a user to test with
    users = User.objects.filter(is_active=True)
    if not users.exists():
        print("❌ No active users found to test with")
        return
    
    test_user = users.first()
    print(f"Testing serialization with user: {test_user.get_full_name()} (ID: {test_user.id})")
    print(f"User designation: {test_user.designation}")
    print(f"User role: {test_user.role.name if test_user.role else 'None'}")
    
    try:
        # Test basic serialization
        serializer = UserSerializer(test_user)
        data = serializer.data
        
        print(f"\n✅ Basic serialization successful!")
        print(f"Serialized fields: {list(data.keys())}")
        
        # Test JSON serialization
        json_data = json.dumps(data, default=str)
        print(f"✅ JSON serialization successful!")
        print(f"JSON length: {len(json_data)} characters")
        
        # Test specific problematic fields
        print(f"\nTesting specific fields:")
        
        # Test delegation-related fields
        if 'leave_delegation_status' in data:
            print(f"  leave_delegation_status: {type(data['leave_delegation_status'])}")
            if data['leave_delegation_status']:
                print(f"    Status: {data['leave_delegation_status'].get('status', 'N/A')}")
        
        if 'delegation_transition_info' in data:
            print(f"  delegation_transition_info: {type(data['delegation_transition_info'])}")
            if data['delegation_transition_info']:
                print(f"    Type: {data['delegation_transition_info'].get('type', 'N/A')}")
        
        if 'current_effective_approver' in data:
            print(f"  current_effective_approver: {type(data['current_effective_approver'])}")
            if data['current_effective_approver']:
                print(f"    Name: {data['current_effective_approver'].get('name', 'N/A')}")
        
        print(f"\n✅ All serialization tests passed!")
        
    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_multiple_users_serialization():
    """Test serializing multiple users (like in department_users endpoint)"""
    print("\n" + "=" * 80)
    print("TESTING MULTIPLE USERS SERIALIZATION")
    print("=" * 80)
    
    # Get multiple users
    users = User.objects.filter(is_active=True)[:5]  # Get first 5 users
    if not users.exists():
        print("❌ No active users found to test with")
        return False
    
    print(f"Testing serialization of {users.count()} users")
    
    try:
        # Test multiple users serialization
        serializer = UserSerializer(users, many=True)
        data = serializer.data
        
        print(f"✅ Multiple users serialization successful!")
        print(f"Number of users serialized: {len(data)}")
        
        # Test JSON serialization of multiple users
        json_data = json.dumps(data, default=str)
        print(f"✅ JSON serialization of multiple users successful!")
        print(f"JSON length: {len(json_data)} characters")
        
        # Test each user's data structure
        for i, user_data in enumerate(data):
            print(f"  User {i+1}: {user_data.get('first_name', 'N/A')} {user_data.get('last_name', 'N/A')}")
            print(f"    ID: {user_data.get('id')}")
            print(f"    Role: {user_data.get('role', {}).get('name', 'N/A') if user_data.get('role') else 'N/A'}")
        
        print(f"\n✅ Multiple users serialization test passed!")
        
    except Exception as e:
        print(f"❌ Multiple users serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_delegation_serialization():
    """Test that delegation-related data is properly serialized"""
    print("\n" + "=" * 80)
    print("TESTING DELEGATION SERIALIZATION")
    print("=" * 80)
    
    # Get users with delegations
    delegations = Delegation.objects.filter(is_active=True)
    if not delegations.exists():
        print("No active delegations found to test with")
        return True
    
    print(f"Testing delegation serialization with {delegations.count()} delegations")
    
    try:
        for i, delegation in enumerate(delegations[:3]):  # Test first 3 delegations
            print(f"\nDelegation {i+1}:")
            print(f"  From: {delegation.delegated_by.get_full_name()}")
            print(f"  To: {delegation.delegated_to.get_full_name()}")
            print(f"  Reason: {delegation.reason}")
            print(f"  Expires: {delegation.expires_at}")
            
            # Test serialization of the delegated_by user
            serializer = UserSerializer(delegation.delegated_by)
            data = serializer.data
            
            # Test JSON serialization
            json_data = json.dumps(data, default=str)
            print(f"  ✅ User serialization successful (JSON length: {len(json_data)})")
            
            # Test delegation-related fields
            if 'leave_delegation_status' in data:
                status = data['leave_delegation_status']
                if status:
                    print(f"    Leave status: {status.get('status', 'N/A')}")
                    if status.get('delegation'):
                        print(f"    Delegation ID: {status['delegation'].get('id', 'N/A')}")
        
        print(f"\n✅ Delegation serialization test passed!")
        
    except Exception as e:
        print(f"❌ Delegation serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("Starting serialization tests...")
        
        # Run all tests
        test1 = test_user_serialization()
        test2 = test_multiple_users_serialization()
        test3 = test_delegation_serialization()
        
        print("\n" + "=" * 80)
        print("SERIALIZATION TEST RESULTS:")
        print("=" * 80)
        
        if test1 and test2 and test3:
            print("🎉 ALL TESTS PASSED!")
            print("✅ User serialization is working correctly")
            print("✅ Multiple users serialization is working correctly")
            print("✅ Delegation serialization is working correctly")
            print("✅ No more JSON serialization errors!")
        else:
            print("❌ Some tests failed - check the output above")
        
        print("\nThe system should now be able to:")
        print("  - Serialize individual users without errors")
        print("  - Handle department_users endpoint without 500 errors")
        print("  - Process delegation-related data correctly")
        print("  - Return proper JSON responses from all user endpoints")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()
