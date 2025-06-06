from django.db import models
from django.conf import settings

class Notification(models.Model):
    ASSIGNMENT = 'assignment'
    STATUS_CHANGE = 'status_change'
    COMMENT = 'comment'
    APPROVAL = 'approval'
    DUE_DATE = 'due_date'

    NOTIFICATION_TYPE_CHOICES = [
        (ASSIGNMENT, 'Assignment'),
        (STATUS_CHANGE, 'Status Change'),
        (COMMENT, 'Comment'),
        (APPROVAL, 'Approval'),
        (DUE_DATE, 'Due Date'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    action_log = models.ForeignKey('action_logs.ActionLog', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} notification for {self.user.get_full_name()}"

    def mark_as_read(self):
        self.is_read = True
        self.save() 