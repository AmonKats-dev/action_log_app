from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from departments.models import Department, DepartmentUnit
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
import random
import string
import re

class Role(models.Model):
    ECONOMIST = 'economist'
    SENIOR_ECONOMIST = 'senior_economist'
    PRINCIPAL_ECONOMIST = 'principal_economist'
    COMMISSIONER = 'commissioner'
    ASSISTANT_COMMISSIONER = 'assistant_commissioner'
    SUPER_ADMIN = 'super_admin'

    ROLE_CHOICES = [
        (ECONOMIST, 'Economist'),
        (SENIOR_ECONOMIST, 'Senior Economist'),
        (PRINCIPAL_ECONOMIST, 'Principal Economist'),
        (COMMISSIONER, 'Commissioner'),
        (ASSISTANT_COMMISSIONER, 'Assistant Commissioner'),
        (SUPER_ADMIN, 'Super Admin'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    can_create_logs = models.BooleanField(default=False)
    can_update_status = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_view_all_logs = models.BooleanField(default=False)
    can_configure = models.BooleanField(default=False)
    can_view_all_users = models.BooleanField(default=False)
    can_assign_to_commissioner = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']  # Alphabetical ordering by role name

class LoginCode(models.Model):
    phone_number = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()
    
    class Meta:
        ordering = ['-created_at']  # Most recent codes first

    @classmethod
    def generate_code(cls):
        """Generate a 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    @classmethod
    def create_for_phone(cls, phone_number):
        """Create a new login code for a phone number"""
        # Invalidate any existing codes for this phone number
        cls.objects.filter(phone_number=phone_number).update(is_used=True)
        
        # Create new code
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=10)  # 10 minutes expiry
        
        return cls.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )

class Delegation(models.Model):
    """Model to track delegation of action log creation rights"""
    DELEGATION_REASON_CHOICES = [
        ('leave', 'Leave'),
        ('other', 'Other'),
    ]
    
    delegated_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='delegations_given')
    delegated_to = models.ForeignKey('User', on_delete=models.CASCADE, related_name='delegations_received')
    delegated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    reason = models.CharField(max_length=10, choices=DELEGATION_REASON_CHOICES, default='other')
    
    class Meta:
        unique_together = ['delegated_by', 'delegated_to']
        verbose_name = 'Delegation'
        verbose_name_plural = 'Delegations'
        ordering = ['-delegated_at', '-id']  # Most recent delegations first, then by ID for consistency
    
    def __str__(self):
        return f"{self.delegated_by.get_full_name()} → {self.delegated_to.get_full_name()}"
    
    def clean(self):
        """Custom validation for delegation rules"""
        from django.core.exceptions import ValidationError
        
        # Check if this is a new delegation or an update
        if not self.pk:  # New delegation
            # For Ag. C/PAP users: ensure they don't have multiple active delegations
            if (self.delegated_by and 
                hasattr(self.delegated_by, 'has_ag_cpap_designation') and 
                self.delegated_by.has_ag_cpap_designation() and 
                self.is_active):
                
                existing_active = Delegation.objects.filter(
                    delegated_by=self.delegated_by,
                    is_active=True
                ).exclude(pk=self.pk)
                
                if existing_active.exists():
                    raise ValidationError(
                        "Ag. C/PAP users can only have one active delegation at a time. "
                        "Please revoke the existing delegation first."
                    )
        
        # Validate leave delegation rules
        self.validate_leave_delegation()
    
    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        
        # Check if delegation has expired and automatically deactivate it
        if self.expires_at and timezone.now() > self.expires_at:
            self.is_active = False
            # Log the automatic expiration for audit purposes
            print(f"INFO: Delegation {self.id} automatically expired at {self.expires_at}")
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_valid(self):
        return self.is_active and not self.is_expired
    
    @property
    def time_until_expiry(self):
        """Get time remaining until delegation expires"""
        if not self.expires_at:
            return None
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else None
    
    @property
    def is_expiring_soon(self):
        """Check if delegation is expiring within the next 24 hours"""
        if not self.expires_at:
            return False
        time_until = self.time_until_expiry
        if time_until is None:
            return False
        # Return True if expiring within 24 hours
        return time_until.total_seconds() <= 24 * 60 * 60

    @classmethod
    def revoke_expired_delegations(cls):
        """Class method to automatically revoke all expired delegations"""
        expired_delegations = cls.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        count = expired_delegations.count()
        expired_delegations.update(is_active=False)
        return count

    def is_leave_delegation(self):
        """Check if this is a leave delegation"""
        return self.reason == 'leave'

    def get_effective_approver(self):
        """Get the effective approver based on delegation status"""
        if not self.is_active or self.is_expired:
            # If delegation is not active or expired, return to original approver
            return self.delegated_by
        
        if self.is_leave_delegation():
            # For leave delegations, the delegate (Ag. AC/PAP) is the effective approver
            return self.delegated_to
        else:
            # For other reasons, return to original approver
            return self.delegated_by

    def validate_leave_delegation(self):
        """Validate leave delegation rules"""
        from django.core.exceptions import ValidationError
        
        if self.reason == 'leave':
            # For leave delegations, ensure the delegate is Ag. AC/PAP
            if not self.delegated_to.has_ag_acpap_designation():
                raise ValidationError(
                    "Leave delegations can only be made to Ag. AC/PAP users. "
                    f"User {self.delegated_to.get_full_name()} does not have Ag. AC/PAP designation."
                )
            
            # Ensure the delegator is Ag. C/PAP
            if not self.delegated_by.has_ag_cpap_designation():
                raise ValidationError(
                    "Only Ag. C/PAP users can create leave delegations. "
                    f"User {self.delegated_by.get_full_name()} does not have Ag. C/PAP designation."
                )
            
            # For leave delegations, expiration date is mandatory
            if not self.expires_at:
                raise ValidationError(
                    "Leave delegations must have an expiration date."
                )

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True)
    department = models.ForeignKey('departments.Department', on_delete=models.PROTECT, null=True)
    employee_id = models.CharField(max_length=50, unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    department_unit = models.ForeignKey(
        DepartmentUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    designation = models.CharField(max_length=100, blank=True, null=True)  # User's title/designation
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def save(self, *args, **kwargs):
        # If user is Commissioner or Assistant Commissioner, don't assign department unit
        if self.role and self.role.name in ['commissioner', 'assistant_commissioner']:
            self.department_unit = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"

    @property
    def is_economist(self):
        return self.role and self.role.name == Role.ECONOMIST

    @property
    def is_senior_economist(self):
        return self.role and self.role.name == Role.SENIOR_ECONOMIST

    @property
    def is_principal_economist(self):
        return self.role and self.role.name == Role.PRINCIPAL_ECONOMIST

    @property
    def is_assistant_commissioner(self):
        return self.role and self.role.name == Role.ASSISTANT_COMMISSIONER

    @property
    def is_commissioner(self):
        return self.role and self.role.name == Role.COMMISSIONER

    @property
    def is_super_admin(self):
        return self.role and self.role.name == Role.SUPER_ADMIN

    def can_create_action_logs(self):
        """Check if user can create action logs based on role and delegations"""
        # Super admin and commissioner can always create logs
        if self.is_super_admin or self.is_commissioner:
            return True
        
        # Check if user has active delegation
        active_delegation = self.delegations_received.filter(is_active=True).first()
        if active_delegation and active_delegation.is_valid:
            return True
        
        # Check role-based permission
        if self.role and self.role.can_create_logs:
            return True
        
        return False

    def can_create_action_logs_by_designation(self):
        """Check if user can create action logs based on designation (for EconomistDashboard)"""
        # Super admin and commissioner can always create logs
        if self.is_super_admin or self.is_commissioner:
            return True
        
        # Check if user has Ag. C/PAP designation
        if self.has_ag_cpap_designation():
            return True
        
        # Check if user has active delegation
        active_delegation = self.delegations_received.filter(is_active=True).first()
        if active_delegation and active_delegation.is_valid:
            return True
        
        return False

    def has_ag_cpap_designation(self):
        """Check if user has Ag. C/PAP designation for delegation management"""
        if not self.designation:
            return False
        
        normalized_designation = self.designation.lower().strip()
        # Replace multiple spaces with single space
        import re
        normalized_designation = re.sub(r'\s+', ' ', normalized_designation)
        
        # Check for Ag. C/PAP designation patterns (highest level)
        is_ag_cpap = (
            normalized_designation == 'ag. c/pap' or 
            normalized_designation == 'ag.c/pap' or
            re.match(r'^ag\.?\s*c\d*/pap$', normalized_designation, re.IGNORECASE)
        )
        
        return is_ag_cpap

    def has_ag_acpap_designation(self):
        """Check if user has Ag. AC/PAP designation for delegation management"""
        if not self.designation:
            return False
        
        normalized_designation = self.designation.lower().strip()
        # Replace multiple spaces with single space
        import re
        normalized_designation = re.sub(r'\s+', ' ', normalized_designation)
        
        # Check for Ag. AC/PAP designation patterns (lower level)
        is_ag_acpap = (
            normalized_designation == 'ag. ac/pap' or 
            normalized_designation == 'ag.ac/pap' or
            re.match(r'^ag\.?\s*ac\d*/pap$', normalized_designation, re.IGNORECASE)
        )
        
        return is_ag_acpap

    def can_manage_delegations(self):
        """Check if user can manage delegations (create, revoke, etc.)"""
        # Super admin and commissioner can always manage delegations
        if self.is_super_admin or self.is_commissioner:
            return True
        
        # Only Ag. C/PAP users can manage delegations (highest level)
        if self.has_ag_cpap_designation():
            return True
        
        # Ag. AC/PAP users CANNOT manage delegations - they need delegation from Ag. C/PAP
        return False

    def has_leave_delegation_responsibilities(self):
        """Check if user has taken over responsibilities due to Ag. C/PAP being on leave"""
        if not self.has_ag_acpap_designation():
            return False
        
        # Check if there's an active leave delegation where this Ag. AC/PAP user is the delegate
        leave_delegation = self.delegations_received.filter(
            is_active=True,
            reason='leave',
            expires_at__gt=timezone.now()
        ).first()
        
        return leave_delegation is not None

    def get_effective_approver_for_action_log(self, action_log=None):
        """Get the effective approver for action logs based on current delegation status"""
        # Super admin and commissioner are always effective approvers
        if self.is_super_admin or self.is_commissioner:
            return self
        
        # If this user has Ag. C/PAP designation, check if they are on leave
        if self.has_ag_cpap_designation():
            # Check if they have an active leave delegation
            leave_delegation = self.delegations_given.filter(
                is_active=True,
                reason='leave',
                expires_at__gt=timezone.now()
            ).first()
            
            if leave_delegation:
                # On leave - return the delegate (Ag. AC/PAP user) as the effective approver
                return leave_delegation.delegated_to
            else:
                # Not on leave - they are the effective approver
                return self
        
        # If this user has Ag. AC/PAP designation, check if they have leave delegation responsibilities
        if self.has_ag_acpap_designation():
            if self.has_leave_delegation_responsibilities():
                # They have taken over responsibilities due to Ag. C/PAP being on leave
                return self
            else:
                # No leave delegation responsibilities, so they are not an effective approver
                return None
        
        # For other users, check if they have active delegation
        active_delegation = self.delegations_received.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if active_delegation:
            return self
        
        return None

    def can_approve_action_logs(self):
        """Check if user can approve action logs based on current delegation status"""
        # First check delegation status - this should override role permissions for leave delegations
        
        # If this user has Ag. C/PAP designation, check if they are on leave
        if self.has_ag_cpap_designation():
            # Check if they have an active leave delegation
            leave_delegation = self.delegations_given.filter(
                is_active=True,
                reason='leave',
                expires_at__gt=timezone.now()
            ).first()
            
            if leave_delegation:
                # On leave - cannot approve, responsibilities delegated to Ag. AC/PAP
                return False
            else:
                # Not on leave - can approve (check role permissions below)
                pass
        
        # If this user has Ag. AC/PAP designation, check if they have leave delegation responsibilities
        if self.has_ag_acpap_designation():
            if self.has_leave_delegation_responsibilities():
                # They have taken over responsibilities due to Ag. C/PAP being on leave
                return True
            else:
                # No leave delegation responsibilities, so they cannot approve
                return False
        
        # Now check role-based permissions (only if no delegation overrides apply)
        # Super admin and commissioner can always approve (unless on leave)
        if self.is_super_admin or self.is_commissioner:
            return True
        
        # For other users, check if they have active delegation
        active_delegation = self.delegations_received.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if active_delegation:
            return True
        
        return False

    def can_delegate_to_user(self, target_user):
        """Check if current user can delegate to the target user"""
        # Super admin and commissioner can delegate to anyone
        if self.is_super_admin or self.is_commissioner:
            return True
        
        # Only Ag. C/PAP users can delegate to anyone
        if self.has_ag_cpap_designation():
            return True
        
        # Ag. AC/PAP users cannot delegate to anyone
        return False

    def get_current_effective_approver(self):
        """Get the current effective approver for action logs (who should handle approvals now)"""
        # First check delegation status - this should override role permissions for leave delegations
        
        # If this user has Ag. C/PAP designation, check if they are on leave
        if self.has_ag_cpap_designation():
            # Check if they have an active leave delegation
            leave_delegation = self.delegations_given.filter(
                is_active=True,
                reason='leave',
                expires_at__gt=timezone.now()
            ).first()
            
            if leave_delegation:
                # On leave - the Ag. AC/PAP user is the effective approver
                return leave_delegation.delegated_to
            else:
                # Not on leave - they are the effective approver (check role permissions below)
                pass
        
        # If this user has Ag. AC/PAP designation, check if they have leave delegation responsibilities
        if self.has_ag_acpap_designation():
            if self.has_leave_delegation_responsibilities():
                # They have taken over responsibilities due to Ag. C/PAP being on leave
                return self
            else:
                # No leave delegation responsibilities, so they are not an effective approver
                return None
        
        # Now check role-based permissions (only if no delegation overrides apply)
        # Super admin and commissioner are always effective approvers (unless on leave)
        if self.is_super_admin or self.is_commissioner:
            return self
        
        # For other users, check if they have active delegation
        active_delegation = self.delegations_received.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if active_delegation:
            return self
        
        return None

    def is_currently_on_leave(self):
        """Check if this user is currently on leave (has active leave delegation)"""
        if not self.has_ag_cpap_designation():
            return False
        
        leave_delegation = self.delegations_given.filter(
            is_active=True,
            reason='leave',
            expires_at__gt=timezone.now()
        ).first()
        
        return leave_delegation is not None
    
    def get_leave_delegation_status(self):
        """Get detailed leave delegation status including expiration information"""
        if not self.has_ag_cpap_designation():
            return None
        
        leave_delegation = self.delegations_given.filter(
            is_active=True,
            reason='leave'
        ).first()
        
        if not leave_delegation:
            return {
                'status': 'available',
                'message': 'Not on leave - available for approvals',
                'delegation': None
            }
        
        if leave_delegation.is_expired:
            return {
                'status': 'expired',
                'message': 'Leave delegation has expired - responsibilities returned',
                'delegation': {
                    'id': leave_delegation.id,
                    'delegated_to_name': leave_delegation.delegated_to.get_full_name(),
                    'delegated_to_id': leave_delegation.delegated_to.id,
                    'delegated_at': leave_delegation.delegated_at,
                    'expires_at': leave_delegation.expires_at
                },
                'expired_at': leave_delegation.expires_at
            }
        
        if leave_delegation.is_expiring_soon:
            time_until_str = str(leave_delegation.time_until_expiry) if leave_delegation.time_until_expiry else 'Unknown'
            return {
                'status': 'expiring_soon',
                'message': f'Leave delegation expires in {time_until_str}',
                'delegation': {
                    'id': leave_delegation.id,
                    'delegated_to_name': leave_delegation.delegated_to.get_full_name(),
                    'delegated_to_id': leave_delegation.delegated_to.id,
                    'delegated_at': leave_delegation.delegated_at,
                    'expires_at': leave_delegation.expires_at
                },
                'expires_at': leave_delegation.expires_at,
                'time_until_expiry': time_until_str
            }
        
        return {
            'status': 'on_leave',
            'message': 'Currently on leave - responsibilities delegated',
            'delegation': {
                'id': leave_delegation.id,
                'delegated_to_name': leave_delegation.delegated_to.get_full_name(),
                'delegated_to_id': leave_delegation.delegated_to.id,
                'delegated_at': leave_delegation.delegated_at,
                'expires_at': leave_delegation.expires_at
            },
            'expires_at': leave_delegation.expires_at,
            'time_until_expiry': str(leave_delegation.time_until_expiry) if leave_delegation.time_until_expiry else 'Unknown'
        }
    
    def get_delegation_transition_info(self):
        """Get information about delegation transitions for UI display"""
        if self.has_ag_cpap_designation():
            leave_status = self.get_leave_delegation_status()
            if leave_status and leave_status['status'] == 'on_leave':
                # Find the Ag. AC/PAP user who has taken over responsibilities
                leave_delegation = leave_status['delegation']
                if leave_delegation:
                    return {
                        'type': 'ag_cpap_on_leave',
                        'status': 'delegated',
                        'delegated_to': {
                            'id': leave_delegation.get('delegated_to_id'),
                            'name': leave_delegation.get('delegated_to_name', 'Unknown User')
                        },
                        'expires_at': leave_delegation.get('expires_at'),
                        'time_until_expiry': leave_delegation.get('time_until_expiry', 'Unknown'),
                        'message': f"Responsibilities delegated to {leave_delegation.get('delegated_to_name', 'Unknown User')} until {leave_delegation.get('expires_at', 'Unknown')}"
                    }
            elif leave_status and leave_status['status'] == 'expired':
                return {
                    'type': 'ag_cpap_returned',
                    'status': 'returned',
                    'message': 'Leave delegation expired - responsibilities returned to you',
                    'expired_at': leave_status.get('expired_at')
                }
            else:
                return {
                    'type': 'ag_cpap_available',
                    'status': 'available',
                    'message': 'Available to handle approvals and rejections'
                }
        
        elif self.has_ag_acpap_designation():
            if self.has_leave_delegation_responsibilities():
                # Find the Ag. C/PAP user who is on leave
                leave_delegation = self.delegations_received.filter(
                    is_active=True,
                    reason='leave',
                    expires_at__gt=timezone.now()
                ).first()
                
                if leave_delegation:
                    return {
                        'type': 'ag_acpap_acting',
                        'status': 'acting',
                        'acting_for': {
                            'id': leave_delegation.delegated_by.id,
                            'name': leave_delegation.delegated_by.get_full_name()
                        },
                        'expires_at': leave_delegation.expires_at,
                        'time_until_expiry': str(leave_delegation.time_until_expiry) if leave_delegation.time_until_expiry else 'Unknown',
                        'message': f"Acting as Ag. C/PAP for {leave_delegation.delegated_by.get_full_name()} until {leave_delegation.expires_at.strftime('%Y-%m-%d %H:%M') if leave_delegation.expires_at else 'Unknown'}"
                    }
            else:
                return {
                    'type': 'ag_acpap_no_delegation',
                    'status': 'no_delegation',
                    'message': 'No leave delegation responsibilities - cannot approve action logs'
                }
        
        return None

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['first_name', 'last_name', 'id']  # Alphabetical by name, then by ID for consistency 