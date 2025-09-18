@echo off
echo ========================================
echo Action Log System - Delegation Expiry
echo ========================================
echo.
echo This script will check for and revoke expired delegations.
echo.

REM Check if we're in the right directory
if not exist "manage.py" (
    echo Error: manage.py not found. Please run this script from the backend directory.
    pause
    exit /b 1
)

echo Checking for expired delegations...
echo.

REM Run the management command
python manage.py revoke_expired_delegations

echo.
echo ========================================
echo Operation completed.
echo ========================================
pause
