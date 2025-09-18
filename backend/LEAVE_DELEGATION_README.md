# Leave Delegation System

## Overview

The Leave Delegation System is a specialized feature that allows **Ag. C/PAP** users to temporarily delegate their responsibilities to **Ag. AC/PAP** users when they go on leave. This ensures continuity of operations and proper approval workflows during absence periods.

## How It Works

### 1. **Leave Delegation Creation**
- **Ag. C/PAP** users can create leave delegations to **Ag. AC/PAP** users
- Leave delegations must have an expiration date
- Only **Ag. C/PAP** users can create leave delegations
- Only **Ag. AC/PAP** users can receive leave delegations

### 2. **Responsibility Transfer**
- When a leave delegation is active, the **Ag. AC/PAP** user takes over all responsibilities
- The approval/rejection flow shifts to the **Ag. AC/PAP** user
- The **Ag. C/PAP** user's responsibilities are temporarily suspended

### 3. **Automatic Return**
- When the delegation expires, responsibilities automatically return to the **Ag. C/PAP** user
- The approval/rejection flow shifts back to the original user
- No manual intervention is required

## Business Rules

### **Leave Delegation Rules**
1. **Only Ag. C/PAP users** can create leave delegations
2. **Only Ag. AC/PAP users** can receive leave delegations
3. **Expiration date is mandatory** for leave delegations
4. **One active leave delegation** per Ag. C/PAP user at a time
5. **Automatic expiration** when the date is reached

### **Responsibility Transfer Rules**
1. **During Leave**: Ag. AC/PAP user becomes the effective approver
2. **After Leave**: Ag. C/PAP user resumes as the effective approver
3. **Seamless Transition**: No interruption to workflow processes
4. **Audit Trail**: All actions are tracked and logged

## API Endpoints

### **Create Leave Delegation**
```http
POST /api/users/delegations/
{
    "delegated_to_id": 123,
    "reason": "leave",
    "expires_at": "2024-02-01T00:00:00Z"
}
```

### **Get User's Leave Delegation Status**
```http
GET /api/users/me/
```
Response includes:
- `has_leave_delegation_responsibilities`: Boolean indicating if user has taken over responsibilities
- `can_approve_action_logs`: Boolean indicating if user can currently approve
- `effective_approver`: Object showing who is currently responsible

### **List All Leave Delegations**
```http
GET /api/users/delegations/?reason=leave
```

## Database Schema

### **Delegation Model**
```python
class Delegation(models.Model):
    DELEGATION_REASON_CHOICES = [
        ('leave', 'Leave'),
        ('other', 'Other'),
    ]
    
    delegated_by = models.ForeignKey('User', related_name='delegations_given')
    delegated_to = models.ForeignKey('User', related_name='delegations_received')
    reason = models.CharField(choices=DELEGATION_REASON_CHOICES, default='other')
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    delegated_at = models.DateTimeField(auto_now_add=True)
```

## User Methods

### **Ag. C/PAP Users**
- `can_manage_delegations()`: Can create and manage delegations
- `get_effective_approver_for_action_log()`: Returns delegate during leave, self otherwise
- `can_approve_action_logs()`: True when not on leave, false when on leave

### **Ag. AC/PAP Users**
- `has_leave_delegation_responsibilities()`: True when taking over due to leave
- `get_effective_approver_for_action_log()`: Returns self when has leave responsibilities
- `can_approve_action_logs()`: True when has leave responsibilities, false otherwise

## Testing

### **Run Leave Delegation Tests**
```bash
cd backend
python test_leave_delegation.py
```

### **Run General Delegation Tests**
```bash
cd backend
python test_delegation_list.py
```

## Admin Interface

### **Django Admin Features**
- **Leave Delegation Column**: Shows which delegations are leave-related
- **Reason Filter**: Filter delegations by reason (leave/other)
- **Effective Approver**: See who is currently responsible
- **Expiration Tracking**: Monitor when delegations expire

### **Admin URL**
```
http://localhost:8000/admin/users/delegation/
```

## Use Cases

### **Scenario 1: Ag. C/PAP Going on Leave**
1. Ag. C/PAP user creates leave delegation to Ag. AC/PAP user
2. Sets expiration date (e.g., 7 days from now)
3. Ag. AC/PAP user immediately takes over responsibilities
4. All approvals/rejections go to Ag. AC/PAP user

### **Scenario 2: Return from Leave**
1. Delegation automatically expires on the set date
2. Responsibilities automatically return to Ag. C/PAP user
3. Approval/rejection flow returns to original user
4. No manual intervention required

### **Scenario 3: Extended Leave**
1. Ag. C/PAP user can extend leave by updating expiration date
2. Ag. AC/PAP user continues to have responsibilities
3. Seamless continuation of workflow

## Benefits

### **Operational Continuity**
- No interruption to approval workflows
- Seamless handover of responsibilities
- Automatic return of responsibilities

### **Compliance & Audit**
- Clear audit trail of responsibility transfers
- Automatic expiration prevents forgotten delegations
- Proper role-based access control

### **User Experience**
- Simple delegation creation process
- Automatic workflow management
- No manual intervention required

## Security Considerations

### **Access Control**
- Only designated users can create leave delegations
- Automatic expiration prevents indefinite delegations
- Role-based validation ensures proper user types

### **Audit Trail**
- All delegation changes are logged
- Responsibility transfers are tracked
- Expiration events are recorded

## Future Enhancements

### **Potential Features**
1. **Notification System**: Alert users when delegations are about to expire
2. **Delegation History**: Track all delegation changes over time
3. **Bulk Operations**: Handle multiple delegations simultaneously
4. **Integration**: Connect with HR systems for automatic leave detection

## Support

For questions or issues with the Leave Delegation System, please refer to:
- **Test Scripts**: `test_leave_delegation.py`, `test_delegation_list.py`
- **Admin Interface**: Django admin panel
- **API Documentation**: REST API endpoints
- **Code Comments**: Inline documentation in models and serializers
