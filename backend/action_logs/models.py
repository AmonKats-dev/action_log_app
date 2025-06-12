from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from departments.models import Department
from django.utils import timezone

User = get_user_model()

class ActionLog(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_approval', 'Pending Approval'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    CLOSURE_STAGE_CHOICES = [
        ('none', 'None'),
        ('unit_head', 'Unit Head'),
        ('assistant_commissioner', 'Assistant Commissioner'),
        ('commissioner', 'Commissioner'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='action_logs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    due_date = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ManyToManyField(User, related_name='assigned_logs')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_logs'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closure_approval_stage = models.CharField(max_length=32, choices=CLOSURE_STAGE_CHOICES, default='none')
    closure_requested_by = models.ForeignKey(User, null=True, blank=True, related_name='closure_requests', on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Action Log'
        verbose_name_plural = 'Action Logs'

    def __str__(self):
        return f"{self.title} - {self.department.name}"

    def can_approve(self, user):
        """Check if user has permission to approve this log"""
        from users.permissions import can_approve_action_log
        return can_approve_action_log(user, self)

    def approve(self, user):
        """Approve the action log"""
        if not self.can_approve(user):
            raise PermissionError("User does not have permission to approve this log")
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, user, reason):
        """Reject the action log with a reason"""
        if not self.can_approve(user):
            raise PermissionError("User does not have permission to reject this log")
        
        self.status = 'rejected'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()

class ActionLogComment(models.Model):
    action_log = models.ForeignKey('ActionLog', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='action_log_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.first_name} {self.user.last_name} on {self.action_log.title}"

    def get_user_email(self):
        return self.user.email if self.user else None

    def get_replies(self):
        try:
            return self.replies.all().select_related('user')
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'action_log_id': self.action_log_id,
            'user_id': self.user_id,
            'comment': self.comment,
            'parent_comment_id': self.parent_comment_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def get_user_data(self):
        if not self.user:
            return {
                'id': 0,
                'first_name': 'Unknown',
                'last_name': 'User',
                'email': ''
            }
        return {
            'id': self.user.id,
            'first_name': self.user.first_name or '',
            'last_name': self.user.last_name or '',
            'email': self.user.email or ''
        }

class ActionLogAttachment(models.Model):
    action_log = models.ForeignKey(ActionLog, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='action_log_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Action Log Attachment'
        verbose_name_plural = 'Action Log Attachments'

    def __str__(self):
        return f"{self.filename} - {self.action_log.title}"

class ActionLogApproval(models.Model):
    action_log = models.ForeignKey(ActionLog, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=ActionLog.STATUS_CHOICES)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Action Log Approval'
        verbose_name_plural = 'Action Log Approvals'
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval by {self.approver.get_full_name()} - {self.get_status_display()}"

class AuditLog(models.Model):
    action_log = models.ForeignKey(ActionLog, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.user.get_full_name()} on {self.action_log.title}" 

class ActionLogAssignmentHistory(models.Model):
    action_log = models.ForeignKey(
        ActionLog,
        on_delete=models.CASCADE,
        related_name='assignment_history'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assignments_made'
    )
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assignment_history'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Action Log Assignment History'
        verbose_name_plural = 'Action Log Assignment Histories'
        ordering = ['-assigned_at']

    def __str__(self):
        return f"Assignment by {self.assigned_by.get_full_name()} at {self.assigned_at}"

    def get_assigned_to_users(self):
        return self.assigned_to.all()

class ActionLogNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='action_log_notifications')
    action_log = models.ForeignKey(ActionLog, on_delete=models.CASCADE, related_name='action_log_notifications')
    comment = models.ForeignKey('ActionLogComment', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Action Log Notification'
        verbose_name_plural = 'Action Log Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.get_full_name()} on log {self.action_log.id}" 