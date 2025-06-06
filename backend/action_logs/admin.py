from django.contrib import admin
from .models import ActionLog, ActionLogComment, ActionLogAttachment, ActionLogApproval, AuditLog

admin.site.register(ActionLog)
admin.site.register(ActionLogComment)
admin.site.register(ActionLogAttachment)
admin.site.register(ActionLogApproval)
admin.site.register(AuditLog) 