from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import ActionLog, ActionLogComment, ActionLogAssignmentHistory, ActionLogNotification
from .serializers import ActionLogSerializer, ActionLogApprovalSerializer, ActionLogAssignmentHistorySerializer, ActionLogNotificationSerializer, ActionLogCommentSerializer
from users.permissions import can_approve_action_log
from django.http import Http404
from users.models import User
from notifications.services import SMSNotificationService
import logging

logger = logging.getLogger(__name__)

class ActionLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role.name in ['commissioner', 'super_admin']:
            return ActionLog.objects.all().select_related('created_by', 'approved_by', 'department').prefetch_related('assigned_to')
        return ActionLog.objects.filter(department=user.department).select_related('created_by', 'approved_by', 'department').prefetch_related('assigned_to')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        # If assigned_to is set, create assignment history and send notifications
        assigned_to_ids = self.request.data.get('assigned_to', [])
        if assigned_to_ids:
            assignment_history = ActionLogAssignmentHistory.objects.create(
                action_log=instance,
                assigned_by=self.request.user,
                comment=self.request.data.get('comment', '')
            )
            assignment_history.assigned_to.set(assigned_to_ids)
            
            # Get assignee names
            assignee_names = [User.objects.get(id=user_id).get_full_name() for user_id in assigned_to_ids]
            assignees_text = ", ".join(assignee_names)
            
            # Send SMS notifications to assigned users
            sms_service = SMSNotificationService()
            for user_id in assigned_to_ids:
                try:
                    user = User.objects.get(id=user_id)
                    if user.phone_number:
                        message = (
                            f"You've been assigned an Action Log\n\n"
                            f"Title: {instance.title}\n"
                            f"Department: PAP\n"
                            f"Priority: {instance.priority}\n"
                            f"Due Date: {instance.due_date.strftime('%Y-%m-%d')}\n"
                            f"Assignee(s): {assignees_text}\n"
                            f"Assigned By: {self.request.user.get_full_name()}\n\n"
                            f"Please check your dashboard for more details."
                        )
                        sms_sent = sms_service.send_notification(user.phone_number, message)
                        if not sms_sent:
                            logger.warning(f"Failed to send SMS notification to user {user.id} for action log {instance.id}")
                except User.DoesNotExist:
                    logger.warning(f"User with ID {user_id} not found when sending SMS notification")
                    continue

    def update(self, request, *args, **kwargs):
        comment_text = request.data.pop('comment', None)
        instance = self.get_object()
        status_changed = False
        old_status = instance.status
        user = request.user
        # --- Closure Approval Workflow ---
        if 'status' in request.data and request.data['status'] == 'closed' and old_status != 'closed':
            # Initiate closure approval workflow
            instance.closure_approval_stage = 'unit_head'
            instance.closure_requested_by = user
            instance.status = 'pending_approval'  # Set to pending_approval until final approval
            instance.save()
            status_changed = True
            # Remove status from request data to prevent overwriting
            request.data.pop('status', None)
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
                   action_log.department == request.user.department):
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
                   action_log.department == request.user.department):
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
        # --- Closure Approval Workflow ---
        if action_log.closure_approval_stage in ['unit_head', 'assistant_commissioner', 'commissioner']:
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
        # --- Default approval logic ---
        if not can_approve_action_log(user, action_log):
            logger.warning(f"[APPROVE] User {user.id} ({user.get_full_name()}) with role {user.role.name} is NOT authorized to approve log {action_log.id} at stage {action_log.closure_approval_stage}")
            return Response(
                {"detail": "You don't have permission to approve this action log"},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            action_log.approve(user)
            return Response(
                self.get_serializer(action_log).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        action_log = self.get_object()
        user = request.user
        # --- Closure Approval Workflow ---
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