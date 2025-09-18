# Automatic Delegation Expiration and Revocation

This document explains how the automatic delegation expiration and revocation system works in the Action Log System.

## Overview

The system automatically checks for expired delegations and revokes them to ensure that users cannot continue to use expired delegation privileges.

## How It Works

### 1. Automatic Expiration Check

- **Model Level**: The `Delegation` model automatically checks expiration on every save operation
- **API Level**: The delegation API automatically checks for expired delegations when fetching the list
- **Signals**: Django signals automatically handle expiration checks

### 2. Expiration Logic

```python
@property
def is_expired(self):
    if self.expires_at:
        return timezone.now() > self.expires_at
    return False

@property
def is_valid(self):
    return self.is_active and not self.is_expired
```

### 3. Automatic Revocation

When a delegation expires:
- `is_active` is automatically set to `False`
- The delegation is marked as inactive
- Users can no longer use the delegated privileges

## Usage

### 1. Creating Delegations with Expiration

```python
# Create a delegation that expires in 7 days
delegation = Delegation.objects.create(
    delegated_by=user1,
    delegated_to=user2,
    expires_at=timezone.now() + timedelta(days=7),
    reason="Temporary delegation for project work"
)
```

### 2. Manual Expiration Check

```python
# Check and revoke all expired delegations
from users.models import Delegation
revoked_count = Delegation.revoke_expired_delegations()
print(f"Revoked {revoked_count} expired delegations")
```

### 3. Management Command

```bash
# Check what would be revoked (dry run)
python manage.py revoke_expired_delegations --dry-run

# Actually revoke expired delegations
python manage.py revoke_expired_delegations
```

### 4. API Endpoints

The delegation API automatically checks for expired delegations:
- `GET /api/users/delegations/` - Automatically checks expiration before returning results
- `POST /api/users/delegations/` - Creates new delegations
- `POST /api/users/delegations/{id}/revoke/` - Manually revoke a delegation

## Frontend Features

### 1. Visual Indicators

- **Expired Delegations**: Show with red tags and "Expired" status
- **Expiring Soon**: Show with orange tags and "Expiring Soon" status
- **Active Delegations**: Show with green tags and "Active" status

### 2. Automatic Status Updates

- Expired delegations show "Expired (Auto-revoke)" status
- Revoke buttons are disabled for expired delegations
- Warning messages indicate when delegations will be automatically revoked
- Status is automatically updated on user login

### 3. Automatic Login Checks

Delegation expiration is automatically checked when users log into the system:
- No manual refresh required
- Automatically updates the status of expired delegations
- Ensures users always see current delegation status

## Configuration

### 1. Cron Job Setup (Recommended)

Set up a cron job to automatically check for expired delegations:

```bash
# Run every hour
0 * * * * cd /path/to/backend && python manage.py revoke_expired_delegations

# Run daily at midnight
0 0 * * * cd /path/to/backend && python manage.py revoke_expired_delegations
```

### 2. Django Settings

Ensure the following is in your Django settings:

```python
# In settings.py
INSTALLED_APPS = [
    # ... other apps
    'users.apps.UsersConfig',  # This registers the signals
]
```

## Testing

### 1. Test Script

Use the provided test script to verify functionality:

```bash
cd backend
python test_delegation_expiry.py
```

### 2. Manual Testing

1. Create a delegation with a past expiration date
2. Check that it's automatically marked as inactive
3. Verify that the user can no longer use delegated privileges

## Benefits

1. **Security**: Prevents unauthorized use of expired delegations
2. **Compliance**: Ensures delegation policies are enforced
3. **Automation**: No manual intervention required
4. **Transparency**: Clear visual indicators of delegation status
5. **Audit Trail**: All expiration events are logged

## Troubleshooting

### Common Issues

1. **Delegations not expiring**: Check if the `expires_at` field is set correctly
2. **Signals not working**: Ensure `users.apps.UsersConfig` is in `INSTALLED_APPS`
3. **Cron job not working**: Check file paths and permissions

### Debug Information

The system provides debug information:
- Console logs when delegations are automatically revoked
- API responses include expiration status
- Frontend shows detailed delegation information

## Future Enhancements

1. **Email Notifications**: Send notifications when delegations are about to expire
2. **Batch Operations**: Bulk operations for multiple delegations
3. **Custom Expiration Rules**: Configurable expiration policies
4. **Audit Reports**: Detailed reports of delegation changes
