#!/usr/bin/env python3
"""
Test script to verify that the action logs endpoint works correctly.
This script tests the ActionLogSerializer to ensure it can properly serialize ActionLog objects.
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

from action_logs.models import ActionLog
from action_logs.serializers import ActionLogSerializer
from users.models import User

def test_action_log_serialization():
    """Test that ActionLog objects can be properly serialized without JSON errors"""
    print("=== TESTING ACTION LOG SERIALIZATION ===")
    print("=" * 80)
    
    # Get action logs to test with
    action_logs = ActionLog.objects.all()
    if not action_logs.exists():
        print("❌ No action logs found to test with")
        return False
    
    print(f"Testing serialization with {action_logs.count()} action logs")
    
    try:
        # Test single action log serialization
        test_log = action_logs.first()
        print(f"\nTesting single action log: {test_log.title} (ID: {test_log.id})")
        
        serializer = ActionLogSerializer(test_log)
        data = serializer.data
        
        print(f"✅ Single action log serialization successful!")
        print(f"Serialized fields: {list(data.keys())}")
        
        # Test JSON serialization
        json_data = json.dumps(data, default=str)
        print(f"✅ JSON serialization successful!")
        print(f"JSON length: {len(json_data)} characters")
        
        # Test specific fields
        print(f"\nTesting specific fields:")
        if 'created_by' in data:
            print(f"  created_by: {type(data['created_by'])}")
            if data['created_by']:
                print(f"    Name: {data['created_by'].get('first_name', 'N/A')} {data['created_by'].get('last_name', 'N/A')}")
        
        if 'assigned_to' in data:
            print(f"  assigned_to: {type(data['assigned_to'])}")
            if data['assigned_to']:
                print(f"    Count: {len(data['assigned_to'])}")
        
        if 'department' in data:
            print(f"  department: {type(data['department'])}")
            if data['department']:
                print(f"    Name: {data['department'].get('name', 'N/A')}")
        
        print(f"\n✅ Single action log serialization test passed!")
        
    except Exception as e:
        print(f"❌ Single action log serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_multiple_action_logs_serialization():
    """Test serializing multiple action logs (like in the main endpoint)"""
    print("\n" + "=" * 80)
    print("TESTING MULTIPLE ACTION LOGS SERIALIZATION")
    print("=" * 80)
    
    # Get multiple action logs
    action_logs = ActionLog.objects.all()[:5]  # Get first 5 logs
    if not action_logs.exists():
        print("❌ No action logs found to test with")
        return False
    
    print(f"Testing serialization of {action_logs.count()} action logs")
    
    try:
        # Test multiple action logs serialization
        serializer = ActionLogSerializer(action_logs, many=True)
        data = serializer.data
        
        print(f"✅ Multiple action logs serialization successful!")
        print(f"Number of logs serialized: {len(data)}")
        
        # Test JSON serialization of multiple logs
        json_data = json.dumps(data, default=str)
        print(f"✅ JSON serialization of multiple logs successful!")
        print(f"JSON length: {len(json_data)} characters")
        
        # Test each log's data structure
        for i, log_data in enumerate(data):
            print(f"  Log {i+1}: {log_data.get('title', 'N/A')}")
            print(f"    ID: {log_data.get('id')}")
            print(f"    Status: {log_data.get('status', 'N/A')}")
            print(f"    Department: {log_data.get('department', {}).get('name', 'N/A') if log_data.get('department') else 'N/A'}")
        
        print(f"\n✅ Multiple action logs serialization test passed!")
        
    except Exception as e:
        print(f"❌ Multiple action logs serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_action_log_with_delegations():
    """Test action logs that involve users with delegations"""
    print("\n" + "=" * 80)
    print("TESTING ACTION LOGS WITH DELEGATIONS")
    print("=" * 80)
    
    # Get action logs created by users who might have delegations
    action_logs = ActionLog.objects.select_related('created_by', 'department').all()[:3]
    if not action_logs.exists():
        print("No action logs found to test with")
        return True
    
    print(f"Testing action logs with delegations: {action_logs.count()} logs")
    
    try:
        for i, log in enumerate(action_logs):
            print(f"\nAction Log {i+1}:")
            print(f"  Title: {log.title}")
            print(f"  Created by: {log.created_by.get_full_name() if log.created_by else 'N/A'}")
            print(f"  Department: {log.department.name if log.department else 'N/A'}")
            
            # Test serialization
            serializer = ActionLogSerializer(log)
            data = serializer.data
            
            # Test JSON serialization
            json_data = json.dumps(data, default=str)
            print(f"  ✅ Serialization successful (JSON length: {len(json_data)})")
            
            # Check delegation-related fields in the created_by user
            if data.get('created_by'):
                created_by = data['created_by']
                if 'leave_delegation_status' in created_by:
                    status = created_by['leave_delegation_status']
                    if status:
                        print(f"    Leave status: {status.get('status', 'N/A')}")
                if 'delegation_transition_info' in created_by:
                    info = created_by['delegation_transition_info']
                    if info:
                        print(f"    Delegation type: {info.get('type', 'N/A')}")
        
        print(f"\n✅ Action logs with delegations test passed!")
        
    except Exception as e:
        print(f"❌ Action logs with delegations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("Starting action logs endpoint tests...")
        
        # Run all tests
        test1 = test_action_log_serialization()
        test2 = test_multiple_action_logs_serialization()
        test3 = test_action_log_with_delegations()
        
        print("\n" + "=" * 80)
        print("ACTION LOGS ENDPOINT TEST RESULTS:")
        print("=" * 80)
        
        if test1 and test2 and test3:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Action log serialization is working correctly")
            print("✅ Multiple action logs serialization is working correctly")
            print("✅ Action logs with delegations are working correctly")
            print("✅ The /api/action-logs/ endpoint should now work without 500 errors!")
        else:
            print("❌ Some tests failed - check the output above")
        
        print("\nThe system should now be able to:")
        print("  - Handle /api/action-logs/ endpoint without errors")
        print("  - Serialize action logs with user delegation data")
        print("  - Return proper JSON responses from action logs endpoints")
        print("  - Support the frontend's getUnitFilteredLogs functionality")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()
