from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db.models import Q, Subquery, OuterRef, Prefetch
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from .models import ActionLog, ActionLogComment, ActionLogAssignmentHistory, ActionLogNotification
from .serializers import ActionLogSerializer, ActionLogApprovalSerializer, ActionLogAssignmentHistorySerializer, ActionLogNotificationSerializer, ActionLogCommentSerializer
from users.permissions import can_approve_action_log
from django.http import Http404
from users.models import User
from notifications.services import SMSNotificationService
import logging
from django.db import models
from rest_framework import permissions

logger = logging.getLogger(__name__)

class ActionLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.info(f"[GET_QUERYSET] User: {user.id} ({user.get_full_name()}) - Role: {user.role.name} - Department: {user.department}")
        
        # If user is commissioner or super admin, return all logs
        if user.role.name in ['commissioner', 'super_admin']:
            logger.info(f"[GET_QUERYSET] User {user.id} is commissioner/super_admin - returning ALL logs")
            return ActionLog.objects.all().select_related('created_by', 'approved_by', 'department').prefetch_related('assigned_to').order_by('-created_at', '-id')
        
        # If user is a unit head, include logs pending their approval for their unit
        user_designation = (user.designation or '').lower()
        user_role = user.role.name.lower()
        is_unit_head = 'head' in user_designation or 'unit_head' in user_role
        if is_unit_head and hasattr(user, 'department_unit') and user.department_unit:
            # Get logs where the first assignee's department_unit matches the user's unit and pending unit head approval
            
            # Get the first assignee for each log from assignment history
            first_assignee = ActionLogAssignmentHistory.objects.filter(
                action_log=OuterRef('pk')
            ).order_by('assigned_at').values('assigned_to__department_unit')[:1]
            
            # Get logs pending unit head approval
            unit_head_logs = ActionLog.objects.filter(
                closure_approval_stage='unit_head',
                status='pending_approval'
            ).annotate(
                first_assignee_unit=Subquery(first_assignee)
            ).filter(
                first_assignee_unit=user.department_unit
            )
            
            # Also include logs from their department or assigned to them
            queryset = ActionLog.objects.filter(
                Q(department=user.department) |
                Q(assigned_to=user)
            ).distinct()
            
            # Add the unit head logs to the queryset
            if unit_head_logs.exists():
                queryset = queryset | unit_head_logs
            
            queryset = queryset.select_related('created_by', 'approved_by', 'department').prefetch_related('assigned_to').distinct().order_by('-created_at', '-id')
            
            logger.info(f"[GET_QUERYSET] User {user.id} is unit head - Queryset count: {queryset.count()}")
            return queryset

        # For other users, show logs from their department OR logs assigned to them
        queryset = ActionLog.objects.filter(
            Q(department=user.department) | 
            Q(assigned_to=user)
        ).select_related('created_by', 'approved_by', 'department').prefetch_related('assigned_to').distinct().order_by('-created_at', '-id')
        
        logger.info(f"[GET_QUERYSET] User {user.id} - Department: {user.department} - Queryset count: {queryset.count()}")
        
        # Log some sample logs for debugging
        sample_logs = queryset[:5]
        for log in sample_logs:
            logger.info(f"[GET_QUERYSET] Sample log {log.id}: department={log.department.id}, assigned_to={list(log.assigned_to.values_list('id', flat=True))}")
        
        return queryset

    def list(self, request, *args, **kwargs):
        logger.info(f"[LIST] User {request.user.id} ({request.user.get_full_name()}) requesting action logs")
        logger.info(f"[LIST] User role: {request.user.role.name} - Department: {request.user.department}")
        
        queryset = self.filter_queryset(self.get_queryset())
        logger.info(f"[LIST] Filtered queryset count: {queryset.count()}")
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info(f"[LIST] Returning paginated response with {len(page)} logs")
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"[LIST] Returning all {len(queryset)} logs")
        
        # Log some details about the returned logs
        for i, log in enumerate(queryset[:3]):  # Log first 3 logs
            logger.info(f"[LIST] Log {i+1}: ID={log.id}, Department={log.department.id}, Assigned_to={list(log.assigned_to.values_list('id', flat=True))}")
        
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        
        # Check if user can create action logs
        if not user.can_create_action_logs():
            raise permissions.PermissionDenied(
                "You do not have permission to create action logs. "
                "Please contact the Commissioner for delegation."
            )
        
        # Set the created_by to the current user
        serializer.save(created_by=user)
        
        # Send SMS notifications to assigned users
        assigned_users = serializer.instance.assigned_to.all()
        if assigned_users.exists():
            sms_service = SMSNotificationService()
            for assigned_user in assigned_users:
                if assigned_user.phone_number:
                    message = (
                        f"Action Log Assignment\n\n"
                        f"Title: {serializer.instance.title}\n"
                        f"Department: PAP\n"
                        f"Priority: {serializer.instance.priority}\n"
                        f"Due Date: {serializer.instance.due_date.strftime('%Y-%m-%d') if serializer.instance.due_date else 'Not set'}\n"
                        f"Assigned By: {user.get_full_name()}\n\n"
                        f"Please check your dashboard for more details."
                    )
                    try:
                        sms_sent = sms_service.send_notification(assigned_user.phone_number, message)
                        if not sms_sent:
                            logger.warning(f"Failed to send SMS notification to user {assigned_user.id} for action log {serializer.instance.id}")
                    except Exception as e:
                        logger.error(f"Error sending SMS notification: {str(e)}")

    def update(self, request, *args, **kwargs):
        comment_text = request.data.pop('comment', None)
        instance = self.get_object()
        status_changed = False
        old_status = instance.status
        user = request.user
        
        # --- New Hierarchical Approval Workflow ---
        if 'status' in request.data and request.data['status'] == 'closed' and old_status != 'closed':
            # Get the original assigner to determine the approval chain
            original_assignment = instance.assignment_history.order_by('assigned_at').first()
            
            if original_assignment:
                original_assigner = original_assignment.assigned_by
                original_assigner_role = original_assigner.role.name.lower()
                
                # Get the first assignee's department unit
                assignee = instance.assigned_to.first() if instance.assigned_to.exists() else None
                assignee_unit = assignee.department_unit if assignee else None
                
                # Determine approval stage based on original assigner's role
                if original_assigner_role == 'commissioner':
                    # Commissioner assigned -> goes to commissioner approval
                    instance.closure_approval_stage = 'commissioner'
                elif original_assigner_role == 'assistant_commissioner':
                    # Assistant Commissioner assigned -> goes to assistant commissioner approval
                    instance.closure_approval_stage = 'assistant_commissioner'
                else:
                    # Unit head or regular staff assigned -> goes to unit head approval
                    instance.closure_approval_stage = 'unit_head'
                
                instance.closure_requested_by = user
                instance.status = 'pending_approval'  # Set to pending_approval until final approval
                instance.save()
                status_changed = True
                # Remove status from request data to prevent overwriting
                request.data.pop('status', None)
                
                logger.info(f"[UPDATE] New approval workflow initiated for log {instance.id}")
                logger.info(f"[UPDATE] Original assigner: {original_assigner.get_full_name()} (role: {original_assigner_role})")
                logger.info(f"[UPDATE] Assignee unit: {assignee_unit}")
                logger.info(f"[UPDATE] Approval stage set to: {instance.closure_approval_stage}")
            else:
                # Fallback to old workflow if no assignment history
                instance.closure_approval_stage = 'unit_head'
                instance.closure_requested_by = user
                instance.status = 'pending_approval'
                instance.save()
                status_changed = True
                request.data.pop('status', None)
                logger.warning(f"[UPDATE] No assignment history found for log {instance.id}, using fallback workflow")
        elif 'status' in request.data and request.data['status'] != old_status:
            status_changed = True
        
        # ... (rest of assignment logic unchanged) ...
        if 'assigned_to' in request.data:
            assignment_history = ActionLogAssignmentHistory.objects.create(
                action_log=instance,
                assigned_by=request.user,
                comment=comment_text
            )
            assignment_history.assigned_to.set(request.data['assigned_to'])
            assignee_names = [User.objects.get(id=user_id).get_full_name() for user_id in request.data['assigned_to']]
            assignees_text = ", ".join(assignee_names)
            sms_service = SMSNotificationService()
            for user_id in request.data['assigned_to']:
                try:
                    user = User.objects.get(id=user_id)
                    if user.phone_number:
                        message = (
                            f"Action Log Assignment Update\n\n"
                            f"Title: {instance.title}\n"
                            f"Department: PAP\n"
                            f"Priority: {instance.priority}\n"
                            f"Due Date: {instance.due_date.strftime('%Y-%m-%d')}\n"
                            f"Assignee(s): {assignees_text}\n"
                            f"Assigned By: {request.user.get_full_name()}\n\n"
                            f"Please check your dashboard for more details."
                        )
                        sms_sent = sms_service.send_notification(user.phone_number, message)
                        if not sms_sent:
                            logger.warning(f"Failed to send SMS notification to user {user.id} for action log {instance.id}")
                except User.DoesNotExist:
                    logger.warning(f"User with ID {user_id} not found when sending SMS notification")
                    continue
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if comment_text or status_changed:
            ActionLogComment.objects.create(
                action_log=instance,
                user=request.user,
                comment=comment_text,
                status=instance.status
            )
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get all comments for a log or add a new comment."""
        try:
            # Check if the action log exists
            try:
                action_log = ActionLog.objects.get(id=pk)
            except ActionLog.DoesNotExist:
                return Response(
                    {'error': f'Action log with id {pk} does not exist'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if user has permission to view the action log
            if not (request.user.role.name in ['commissioner', 'super_admin'] or 
                   action_log.department == request.user.department or
                   request.user in action_log.assigned_to.all()):
                return Response(
                    {'error': 'You do not have permission to view this action log'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if request.method == 'POST':
                logger.info(f"Creating comment for action log {pk} by user {request.user.id}")
                
                parent = None
                parent_id = request.data.get('parent_id')
                if parent_id:
                    try:
                        parent = ActionLogComment.objects.get(id=parent_id)
                    except ActionLogComment.DoesNotExist:
                        parent = None

                comment = ActionLogComment.objects.create(
                    action_log=action_log,
                    user=request.user,
                    comment=request.data.get('comment'),
                    parent_comment=parent
                )
                logger.info(f"Comment {comment.id} created successfully")
                
                # Create notifications
                notified_user_ids = set()
                
                # Create notification for assigned users
                assigned_users = action_log.assigned_to.all()
                for user in assigned_users:
                    if user != request.user:  # Don't notify the commenter
                        ActionLogNotification.objects.create(
                            user=user,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(user.id)
                        logger.info(f"Notification created for assigned user {user.id}")

                # Standard notification logic: assigned users, parent comment author, root comment author
                # Notify assigned users (except sender)
                for user in assigned_users:
                    if user != request.user and user.id not in notified_user_ids:
                        ActionLogNotification.objects.create(
                            user=user,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(user.id)
                        logger.info(f"Notification created for assigned user {user.id}")

                # If this is a reply, notify the parent comment's author and root/original comment's author
                if parent:
                    parent_author = parent.user
                    if parent_author != request.user and parent_author.id not in notified_user_ids:
                        ActionLogNotification.objects.create(
                            user=parent_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(parent_author.id)
                        logger.info(f"Notification created for parent comment author {parent_author.id}")

                    # Notify root comment author if different from parent author
                    root_comment = parent
                    while root_comment.parent_comment:
                        root_comment = root_comment.parent_comment
                    
                    root_author = root_comment.user
                    if root_author != request.user and root_author.id not in notified_user_ids:
                        ActionLogNotification.objects.create(
                            user=root_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(root_author.id)
                        logger.info(f"Notification created for root comment author {root_author.id}")

                return Response(ActionLogCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
            
            # GET request - return all comments
            comments = ActionLogComment.objects.filter(action_log=action_log, parent_comment=None).select_related('user')
            serializer = ActionLogCommentSerializer(comments, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error in comments action: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def mark_comments_viewed(self, request, pk=None):
        """Mark all comments for a log as viewed by the current user."""
        try:
            # Check if the action log exists
            try:
                action_log = ActionLog.objects.get(id=pk)
            except ActionLog.DoesNotExist:
                return Response(
                    {'error': f'Action log with id {pk} does not exist'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if user has permission to view the action log
            if not (request.user.role.name in ['commissioner', 'super_admin'] or 
                   action_log.department == request.user.department or
                   request.user in action_log.assigned_to.all()):
                return Response(
                    {'error': 'You do not have permission to view this action log'},
                    status=status.HTTP_403_FORBIDDEN
                )

            with transaction.atomic():
                # Get all comments for the log
                comments = ActionLogComment.objects.filter(
                    action_log_id=pk
                )
                # Mark each comment as viewed
                comments.update(is_viewed=True)
                # Fix for MySQL: get IDs first, then update replies
                parent_comment_ids = list(comments.values_list('id', flat=True))
                if parent_comment_ids:
                    ActionLogComment.objects.filter(
                        parent_comment_id__in=parent_comment_ids
                    ).update(is_viewed=True)
            
            return Response({'message': 'Comments marked as viewed'})
        except Exception as e:
            logger.error(f"Error in mark_comments_viewed: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        action_log = self.get_object()
        user = request.user
        logger.info(f"[APPROVE] User {user.id} ({user.get_full_name()}) attempting to approve log {action_log.id} at stage {action_log.closure_approval_stage}")
        
        # --- New Hierarchical Approval Workflow ---
        if action_log.closure_approval_stage in ['unit_head', 'assistant_commissioner', 'commissioner']:
            # Get the original assigner to determine the approval chain
            original_assignment = action_log.assignment_history.order_by('assigned_at').first()
            
            if original_assignment:
                original_assigner = original_assignment.assigned_by
                original_assigner_role = original_assigner.role.name.lower()
                
                # Get the first assignee's department unit
                assignee = action_log.assigned_to.first() if action_log.assigned_to.exists() else None
                assignee_unit = assignee.department_unit if assignee else None
                
                # Check if the current user is authorized to approve at this stage
                user_role = user.role.name.lower()
                user_designation = (user.designation or '').lower()
                is_unit_head = (
                    'head' in user_designation or 
                    'unit_head' in user_role or 
                    user_designation.endswith('/pap') or
                    user_designation.startswith('pas')
                )
                is_in_same_unit = assignee_unit and assignee_unit == user.department_unit
                
                # Check if user has Ag. C/PAP designation
                is_ag_cpap = (
                    'ag. c/pap' in user_designation or 
                    'ag.c/pap' in user_designation or
                    user_designation == 'ag. c/pap' or
                    user_designation == 'ag.c/pap'
                )
                
                logger.info(f"[APPROVE] Authorization check - User: {user.get_full_name()}")
                logger.info(f"[APPROVE] User designation: {user_designation}, role: {user_role}")
                logger.info(f"[APPROVE] Is unit head: {is_unit_head}, in same unit: {is_in_same_unit}")
                logger.info(f"[APPROVE] Is Ag. C/PAP: {is_ag_cpap}")
                logger.info(f"[APPROVE] Assignee unit: {assignee_unit}, User unit: {user.department_unit}")
                
                can_approve_at_stage = False
                
                if action_log.closure_approval_stage == 'unit_head':
                    # Unit head approval: only unit heads in the same unit as the assignee can approve
                    can_approve_at_stage = is_unit_head and is_in_same_unit
                elif action_log.closure_approval_stage == 'assistant_commissioner':
                    # Assistant commissioner approval: only assistant commissioners can approve
                    can_approve_at_stage = user_role == 'assistant_commissioner'
                elif action_log.closure_approval_stage == 'commissioner':
                    # Commissioner approval: only commissioners can approve
                    can_approve_at_stage = user_role == 'commissioner'
                
                if not can_approve_at_stage:
                    logger.warning(f"[APPROVE] User {user.id} ({user.get_full_name()}) is NOT authorized to approve at stage {action_log.closure_approval_stage}")
                    return Response(
                        {"detail": f"You don't have permission to approve this action log at the {action_log.closure_approval_stage} stage"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Check if user can approve and close the action log
                can_approve_and_close = False
                
                # If user is Ag. C/PAP, check delegation reason to determine approval flow
                if is_ag_cpap:
                    # Check if user has active delegation with "Leave" reason
                    active_delegation = user.delegations_received.filter(is_active=True).first()
                    is_leave_delegation = active_delegation and active_delegation.reason == 'leave'
                    
                    if is_leave_delegation:
                        # For "Leave" delegation, skip to Ag. AC/PAP approval instead of immediately closing
                        logger.info(f"[APPROVE] Ag. C/PAP user {user.id} has 'Leave' delegation - skipping to Ag. AC/PAP approval")
                        
                        # Move to next stage in approval chain
                        prev_stage = action_log.closure_approval_stage
                        if action_log.closure_approval_stage == 'unit_head':
                            action_log.closure_approval_stage = 'assistant_commissioner'
                        elif action_log.closure_approval_stage == 'assistant_commissioner':
                            action_log.closure_approval_stage = 'commissioner'
                        elif action_log.closure_approval_stage == 'commissioner':
                            action_log.closure_approval_stage = 'closed'
                            action_log.status = 'closed'
                        
                        action_log.save()
                        logger.info(f"[APPROVE] Log {action_log.id} stage changed from {prev_stage} to {action_log.closure_approval_stage} due to Leave delegation")
                        
                        # Add approval comment
                        comment_text = request.data.get('comment', '')
                        if comment_text:
                            ActionLogComment.objects.create(
                                action_log=action_log,
                                user=user,
                                comment=comment_text,
                                status=action_log.status,
                                is_approved=True
                            )
                        
                        return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
                    else:
                        # For "Other" or no delegation reason, immediately approve and close
                        can_approve_and_close = True
                        logger.info(f"[APPROVE] Ag. C/PAP user {user.id} can immediately approve and close log {action_log.id}")
                
                # If user is Ag. AC/PAP, check if they have leave delegation responsibilities
                elif user.has_ag_acpap_designation():
                    if user.has_leave_delegation_responsibilities():
                        # They have taken over responsibilities due to Ag. C/PAP being on leave
                        can_approve_and_close = True
                        logger.info(f"[APPROVE] Ag. AC/PAP user {user.id} has leave delegation responsibilities - can approve and close log {action_log.id}")
                    else:
                        # No leave delegation responsibilities, so they cannot approve and close
                        can_approve_and_close = False
                        logger.info(f"[APPROVE] Ag. AC/PAP user {user.id} has no leave delegation responsibilities - cannot approve and close log {action_log.id}")
                
                # If user can approve and close, do it now
                if can_approve_and_close:
                    prev_stage = action_log.closure_approval_stage
                    action_log.closure_approval_stage = 'closed'
                    action_log.status = 'closed'
                    action_log.save()
                    logger.info(f"[APPROVE] User {user.id} immediately approved and closed log {action_log.id} from stage {prev_stage}")
                    
                    # Add approval comment
                    comment_text = request.data.get('comment', '')
                    if comment_text:
                        ActionLogComment.objects.create(
                            action_log=action_log,
                            user=user,
                            comment=comment_text,
                            status=action_log.status,
                            is_approved=True
                        )
                    
                    return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
                
                # For users who cannot approve and close, follow the regular approval chain
                prev_stage = action_log.closure_approval_stage
                if action_log.closure_approval_stage == 'unit_head':
                    action_log.closure_approval_stage = 'assistant_commissioner'
                elif action_log.closure_approval_stage == 'assistant_commissioner':
                    action_log.closure_approval_stage = 'commissioner'
                elif action_log.closure_approval_stage == 'commissioner':
                    action_log.closure_approval_stage = 'closed'
                    action_log.status = 'closed'
                
                action_log.save()
                logger.info(f"[APPROVE] Log {action_log.id} stage changed from {prev_stage} to {action_log.closure_approval_stage}")
                
                # Add approval comment
                comment_text = request.data.get('comment', '')
                if comment_text:
                    ActionLogComment.objects.create(
                        action_log=action_log,
                        user=user,
                        comment=comment_text,
                        status=action_log.status,
                        is_approved=True
                    )
                
                return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
            else:
                # Fallback to old workflow if no assignment history
                logger.warning(f"[APPROVE] No assignment history found for log {action_log.id}, using fallback workflow")
                return self._fallback_approve_workflow(action_log, user, request)
        else:
            # Fallback to old workflow for non-closure approval stages
            return self._fallback_approve_workflow(action_log, user, request)
    
    def _fallback_approve_workflow(self, action_log, user, request):
        """Fallback to the old approval workflow"""
        # Check if user has Ag. C/PAP designation
        user_designation = (user.designation or '').lower()
        is_ag_cpap = (
            'ag. c/pap' in user_designation or 
            'ag.c/pap' in user_designation or
            user_designation == 'ag. c/pap' or
            user_designation == 'ag.c/pap'
        )
        

        
        # Check if user can approve and close the action log
        can_approve_and_close = False
        
        # If user is Ag. C/PAP, check delegation reason to determine approval flow
        if is_ag_cpap:
            # Check if user has active delegation with "Leave" reason
            active_delegation = user.delegations_received.filter(is_active=True).first()
            is_leave_delegation = active_delegation and active_delegation.reason == 'leave'
            
            if is_leave_delegation:
                # For "Leave" delegation, skip to Ag. AC/PAP approval instead of immediately closing
                logger.info(f"[APPROVE] Ag. C/PAP user {user.id} has 'Leave' delegation in fallback workflow - skipping to Ag. AC/PAP approval")
                
                # Move to next stage in approval chain
                prev_stage = action_log.closure_approval_stage
                if action_log.closure_approval_stage == 'unit_head':
                    action_log.closure_approval_stage = 'assistant_commissioner'
                elif action_log.closure_approval_stage == 'assistant_commissioner':
                    action_log.closure_approval_stage = 'commissioner'
                elif action_log.closure_approval_stage == 'commissioner':
                    action_log.closure_approval_stage = 'closed'
                    action_log.status = 'closed'
                
                action_log.save()
                logger.info(f"[APPROVE] Log {action_log.id} stage changed from {prev_stage} to {action_log.closure_approval_stage} due to Leave delegation in fallback workflow")
                
                # Add approval comment
                comment_text = request.data.get('comment', '')
                if comment_text:
                    ActionLogComment.objects.create(
                        action_log=action_log,
                        user=user,
                        comment=comment_text,
                        status=action_log.status,
                        is_approved=True
                    )
                
                return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
            else:
                # For "Other" or no delegation reason, immediately approve and close
                can_approve_and_close = True
                logger.info(f"[APPROVE] Ag. C/PAP user {user.id} can immediately approve and close log {action_log.id} in fallback workflow")
        
        # If user is Ag. AC/PAP, check if they have leave delegation responsibilities
        elif user.has_ag_acpap_designation():
            if user.has_leave_delegation_responsibilities():
                # They have taken over responsibilities due to Ag. C/PAP being on leave
                can_approve_and_close = True
                logger.info(f"[APPROVE] Ag. AC/PAP user {user.id} has leave delegation responsibilities - can approve and close log {action_log.id} in fallback workflow")
            else:
                # No leave delegation responsibilities, so they cannot approve and close
                can_approve_and_close = False
                logger.info(f"[APPROVE] Ag. AC/PAP user {user.id} has no leave delegation responsibilities - cannot approve and close log {action_log.id} in fallback workflow")
        
        # If user can approve and close, do it now
        if can_approve_and_close:
            prev_stage = action_log.closure_approval_stage
            action_log.closure_approval_stage = 'closed'
            action_log.status = 'closed'
            action_log.save()
            logger.info(f"[APPROVE] User {user.id} immediately approved and closed log {action_log.id} from stage {prev_stage} in fallback workflow")
            
            # Add approval comment
            comment_text = request.data.get('comment', '')
            if comment_text:
                ActionLogComment.objects.create(
                    action_log=action_log,
                    user=user,
                    comment=comment_text,
                    status=action_log.status,
                    is_approved=True
                )
            
            return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
        
        # For users who cannot approve and close, follow the regular approval chain
        prev_stage = action_log.closure_approval_stage
        # Move to next stage or close
        if action_log.closure_approval_stage == 'unit_head':
            action_log.closure_approval_stage = 'assistant_commissioner'
        elif action_log.closure_approval_stage == 'assistant_commissioner':
            action_log.closure_approval_stage = 'commissioner'
        elif action_log.closure_approval_stage == 'commissioner':
            action_log.closure_approval_stage = 'closed'
            action_log.status = 'closed'  # Only now set to closed
        action_log.save()
        logger.info(f"[APPROVE] Log {action_log.id} stage changed from {prev_stage} to {action_log.closure_approval_stage}")
        # Add approval comment
        comment_text = request.data.get('comment', '')
        if comment_text:
            ActionLogComment.objects.create(
                action_log=action_log,
                user=user,
                comment=comment_text,
                status=action_log.status,
                is_approved=True
            )
        return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        action_log = self.get_object()
        user = request.user
        
        # --- Updated Rejection Workflow: Ag. C/PAP users and Ag. AC/PAP users with leave delegation can reject ---
        if action_log.closure_approval_stage in ['unit_head', 'assistant_commissioner', 'commissioner']:
            # Check if the current user can reject based on delegation status
            can_reject = False
            
            # Check if user has Ag. C/PAP designation
            user_designation = (user.designation or '').lower()
            is_ag_cpap = (
                'ag. c/pap' in user_designation or 
                'ag.c/pap' in user_designation or
                user_designation == 'ag. c/pap' or
                user_designation == 'ag.c/pap'
            )
            
            if is_ag_cpap:
                # Check if Ag. C/PAP user is on leave
                active_delegation = user.delegations_received.filter(is_active=True).first()
                is_leave_delegation = active_delegation and active_delegation.reason == 'leave'
                
                if not is_leave_delegation:
                    # Not on leave - can reject
                    can_reject = True
                    logger.info(f"[REJECT] Ag. C/PAP user {user.id} can reject - not on leave")
                else:
                    # On leave - cannot reject, responsibilities delegated to Ag. AC/PAP
                    can_reject = False
                    logger.info(f"[REJECT] Ag. C/PAP user {user.id} cannot reject - on leave")
            
            # Check if user is Ag. AC/PAP with leave delegation responsibilities
            elif user.has_ag_acpap_designation():
                if user.has_leave_delegation_responsibilities():
                    # They have taken over responsibilities due to Ag. C/PAP being on leave
                    can_reject = True
                    logger.info(f"[REJECT] Ag. AC/PAP user {user.id} can reject - has leave delegation responsibilities")
                else:
                    # No leave delegation responsibilities, so they cannot reject
                    can_reject = False
                    logger.info(f"[REJECT] Ag. AC/PAP user {user.id} cannot reject - no leave delegation responsibilities")
            
            if not can_reject:
                logger.warning(f"[REJECT] User {user.id} ({user.get_full_name()}) is NOT authorized to reject")
                return Response(
                    {"detail": "You are not authorized to reject action logs"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get the original assigner to determine the rejection chain
            original_assignment = action_log.assignment_history.order_by('assigned_at').first()
            
            if original_assignment:
                original_assigner = original_assignment.assigned_by
                original_assigner_role = original_assigner.role.name.lower()
                
                # Determine the rejection behavior based on the original assigner's role
                if original_assigner_role == 'commissioner':
                    # Commissioner assigned -> rejection goes back to requester
                    action_log.closure_approval_stage = 'none'
                    action_log.status = 'in_progress'
                elif original_assigner_role == 'assistant_commissioner':
                    # Assistant Commissioner assigned -> rejection goes back to requester
                    action_log.closure_approval_stage = 'none'
                    action_log.status = 'in_progress'
                else:
                    # Unit Head or regular staff assigned -> rejection goes back to requester
                    action_log.closure_approval_stage = 'none'
                    action_log.status = 'in_progress'
                
                action_log.save()
                logger.info(f"[REJECT] Log {action_log.id} rejected by Ag. C/PAP user {user.id} at stage {action_log.closure_approval_stage}, returned to requester")
                
                # Add rejection comment
                comment_text = request.data.get('comment', '')
                if comment_text:
                    ActionLogComment.objects.create(
                        action_log=action_log,
                        user=user,
                        comment=comment_text,
                        status=action_log.status,
                        is_approved=False
                    )
                
                return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
            else:
                # Fallback to old workflow if no assignment history
                logger.warning(f"[REJECT] No assignment history found for log {action_log.id}, using fallback workflow")
                return self._fallback_reject_workflow(action_log, user, request)
        else:
            # Fallback to old workflow for non-closure approval stages
            return self._fallback_reject_workflow(action_log, user, request)
    
    def _fallback_reject_workflow(self, action_log, user, request):
        """Fallback to the old rejection workflow"""
        # Check if the current user can reject based on delegation status
        can_reject = False
        
        # Check if user has Ag. C/PAP designation
        user_designation = (user.designation or '').lower()
        is_ag_cpap = (
            'ag. c/pap' in user_designation or 
            'ag.c/pap' in user_designation or
            user_designation == 'ag. c/pap' or
            user_designation == 'ag.c/pap'
        )
        
        if is_ag_cpap:
            # Check if Ag. C/PAP user is on leave
            active_delegation = user.delegations_received.filter(is_active=True).first()
            is_leave_delegation = active_delegation and active_delegation.reason == 'leave'
            
            if not is_leave_delegation:
                # Not on leave - can reject
                can_reject = True
                logger.info(f"[REJECT] Ag. C/PAP user {user.id} can reject in fallback workflow - not on leave")
            else:
                # On leave - cannot reject, responsibilities delegated to Ag. AC/PAP
                can_reject = False
                logger.info(f"[REJECT] Ag. C/PAP user {user.id} cannot reject in fallback workflow - on leave")
        
        # Check if user is Ag. AC/PAP with leave delegation responsibilities
        elif user.has_ag_acpap_designation():
            if user.has_leave_delegation_responsibilities():
                # They have taken over responsibilities due to Ag. C/PAP being on leave
                can_reject = True
                logger.info(f"[REJECT] Ag. AC/PAP user {user.id} can reject in fallback workflow - has leave delegation responsibilities")
            else:
                # No leave delegation responsibilities, so they cannot reject
                can_reject = False
                logger.info(f"[REJECT] Ag. AC/PAP user {user.id} cannot reject in fallback workflow - no leave delegation responsibilities")
        
        if not can_reject:
            logger.warning(f"[REJECT] User {user.id} ({user.get_full_name()}) is NOT authorized to reject in fallback workflow")
            return Response(
                {"detail": "You are not authorized to reject action logs"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # --- Default rejection logic ---
        if action_log.closure_approval_stage in ['assistant_commissioner', 'commissioner']:
            # Move down a stage
            if action_log.closure_approval_stage == 'assistant_commissioner':
                action_log.closure_approval_stage = 'unit_head'
            elif action_log.closure_approval_stage == 'commissioner':
                action_log.closure_approval_stage = 'assistant_commissioner'
            action_log.status = 'in_progress'
            action_log.save()
            # Add rejection comment
            comment_text = request.data.get('comment', '')
            if comment_text:
                ActionLogComment.objects.create(
                    action_log=action_log,
                    user=user,
                    comment=comment_text,
                    status=action_log.status,
                    is_approved=False
                )
            return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
        elif action_log.closure_approval_stage == 'unit_head':
            # Rejected at unit head, return to requester
            action_log.closure_approval_stage = 'none'
            action_log.status = 'in_progress'
            action_log.save()
            comment_text = request.data.get('comment', '')
            if comment_text:
                ActionLogComment.objects.create(
                    action_log=action_log,
                    user=user,
                    comment=comment_text,
                    status=action_log.status,
                    is_approved=False
                )
            return Response(self.get_serializer(action_log).data, status=status.HTTP_200_OK)
        # --- Default rejection logic ---
        serializer = ActionLogApprovalSerializer(
            data=request.data,
            context={'request': request, 'action_log': action_log}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            action_log.reject(
                user,
                serializer.validated_data.get('rejection_reason', '')
            )
            return Response(
                self.get_serializer(action_log).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def assignment_history(self, request, pk=None):
        try:
            action_log = self.get_object()
            history = (
                action_log.assignment_history
                .select_related('assigned_by')
                .prefetch_related('assigned_to')
                .order_by('-assigned_at')
            )
            serializer = ActionLogAssignmentHistorySerializer(history, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def unread_notifications(self, request, pk=None):
        """Get unread notification count for the current user and this action log"""
        action_log = self.get_object()
        count = ActionLogNotification.objects.filter(action_log=action_log, user=request.user, is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_notifications_read(self, request, pk=None):
        """Mark all notifications for this action log as read for the current user"""
        action_log = self.get_object()
        ActionLogNotification.objects.filter(
            action_log=action_log,
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'marked_read': True})

class ActionLogCommentViewSet(viewsets.ModelViewSet):
    queryset = ActionLogComment.objects.all()
    serializer_class = ActionLogCommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        logger.info(f"Creating comment for action log {self.request.data.get('action_log')} by user {self.request.user.id}")
        
        action_log_id = self.request.data.get('action_log')
        parent_id = self.request.data.get('parent_comment_id')
        
        logger.info(f"Action log ID: {action_log_id}")
        logger.info(f"Parent comment ID: {parent_id}")
        
        try:
            action_log = ActionLog.objects.get(id=action_log_id)
            logger.info(f"Found action log: {action_log.id} - {action_log.title}")
            
            # Save the comment
            comment = serializer.save(user=self.request.user, action_log=action_log)
            logger.info(f"Comment {comment.id} created successfully")
            
            # Create notifications
            notified_user_ids = set()
            
            # Create notification for assigned users
            assigned_users = action_log.assigned_to.all()
            logger.info(f"Number of assigned users: {assigned_users.count()}")
            for user in assigned_users:
                logger.info(f"Checking assigned user: {user.id} ({user.username})")
                if user != self.request.user:  # Don't notify the commenter
                    ActionLogNotification.objects.create(
                        user=user,
                        action_log=action_log,
                        comment=comment
                    )
                    notified_user_ids.add(user.id)
                    logger.info(f"Notification created for assigned user {user.id}")
                else:
                    logger.info(f"Skipping notification for sender: {user.id} ({user.username})")

            # Standard notification logic: assigned users, parent comment author, root comment author
            # Notify assigned users (except sender)
            for user in assigned_users:
                if user != self.request.user and user.id not in notified_user_ids:
                    ActionLogNotification.objects.create(
                        user=user,
                        action_log=action_log,
                        comment=comment
                    )
                    notified_user_ids.add(user.id)
                    logger.info(f"Notification created for assigned user {user.id}")

            # If this is a reply, notify the parent comment's author and root/original comment's author
            if parent_id:
                try:
                    parent_comment = ActionLogComment.objects.get(id=parent_id)
                    parent_author = parent_comment.user
                    logger.info(f"Parent author: {parent_author.id} ({parent_author.username})")
                    logger.info(f"Sender: {self.request.user.id} ({self.request.user.username})")
                    if parent_author != self.request.user and parent_author.id not in notified_user_ids:
                        ActionLogNotification.objects.create(
                            user=parent_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(parent_author.id)
                        logger.info(f"Notification created for parent comment author {parent_author.id}")
                    else:
                        logger.info(f"Skipping parent author notification - already notified or is sender")
                    # Traverse up to the root/original comment
                    root_comment = parent_comment
                    while root_comment.parent_comment:
                        root_comment = root_comment.parent_comment
                    root_author = root_comment.user
                    logger.info(f"Root author: {root_author.id} ({root_author.username})")
                    if root_author != self.request.user:
                        ActionLogNotification.objects.create(
                            user=root_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(root_author.id)
                        logger.info(f"Notification created for root comment author {root_author.id}")
                    else:
                        logger.info(f"Skipping root author notification - is sender")
                except ActionLogComment.DoesNotExist:
                    logger.info("[DEBUG] Parent comment does not exist for notification.")
                    pass

            logger.info(f"Total users notified: {len(notified_user_ids)}")
            logger.info(f"Notified user IDs: {notified_user_ids}")
            
        except ActionLog.DoesNotExist:
            logger.error(f"Action log not found: {action_log_id}")
            raise Http404("Action log not found") 