#!/bin/bash

echo "========================================"
echo "Action Log System - Delegation Expiry"
echo "========================================"
echo ""
echo "This script will check for and revoke expired delegations."
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the backend directory."
    exit 1
fi

echo "Checking for expired delegations..."
echo ""

# Run the management command
python manage.py revoke_expired_delegations

echo ""
echo "========================================"
echo "Operation completed."
echo "========================================"
