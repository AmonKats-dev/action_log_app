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
        # If assigned_to is set, create assignment history
        assigned_to_ids = self.request.data.get('assigned_to', [])
        if assigned_to_ids:
            assignment_history = ActionLogAssignmentHistory.objects.create(
                action_log=instance,
                assigned_by=self.request.user,
                comment=self.request.data.get('comment', '')
            )
            assignment_history.assigned_to.set(assigned_to_ids)

    def update(self, request, *args, **kwargs):
        # Get the comment from the request data
        comment_text = request.data.pop('comment', None)
        
        # Get the current instance
        instance = self.get_object()
        
        # Check if assigned_to is being updated
        if 'assigned_to' in request.data:
            # Create assignment history record
            assignment_history = ActionLogAssignmentHistory.objects.create(
                action_log=instance,
                assigned_by=request.user,
                comment=comment_text
            )
            # Add the assigned users
            assignment_history.assigned_to.set(request.data['assigned_to'])
        
        # Perform the update
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # If there's a comment, create a new comment record
        if comment_text:
            ActionLogComment.objects.create(
                action_log=instance,
                user=request.user,
                comment=comment_text
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
                print("\n=== Comment Creation Started ===")
                print(f"Request method: {request.method}")
                print(f"Request user: {request.user.id} ({request.user.username})")
                print(f"Request data: {request.data}")
                
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
                print(f"Comment created with ID: {comment.id}")
                
                # Create notifications
                print("\n=== Creating Notifications ===")
                notified_user_ids = set()
                print(f"Sender user ID: {request.user.id}")
                
                # Create notification for assigned users
                assigned_users = action_log.assigned_to.all()
                print(f"Number of assigned users: {assigned_users.count()}")
                for user in assigned_users:
                    print(f"Checking assigned user: {user.id} ({user.username})")
                    if user != request.user:  # Don't notify the commenter
                        ActionLogNotification.objects.create(
                            user=user,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(user.id)
                        print(f"Notified assigned user: {user.id} ({user.username})")
                    else:
                        print(f"Skipping notification for sender: {user.id} ({user.username})")

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
                        print(f"Notified assigned user: {user.id} ({user.username})")
                    else:
                        print(f"Skipping notification for sender or already notified: {user.id} ({user.username})")

                # If this is a reply, notify the parent comment's author and root/original comment's author
                if parent_id:
                    try:
                        parent_comment = ActionLogComment.objects.get(id=parent_id)
                        parent_author = parent_comment.user
                        print(f"[DEBUG] Parent author: {parent_author.id} ({parent_author.username})")
                        print(f"[DEBUG] Sender: {request.user.id} ({request.user.username})")
                        if parent_author != request.user and parent_author.id not in notified_user_ids:
                            ActionLogNotification.objects.create(
                                user=parent_author,
                                action_log=action_log,
                                comment=comment
                            )
                            notified_user_ids.add(parent_author.id)
                            print(f"[DEBUG] Notified parent comment author: {parent_author.id} ({parent_author.username})")
                        else:
                            print(f"[DEBUG] Skipping parent author notification - already notified or is sender")
                        # Traverse up to the root/original comment
                        root_comment = parent_comment
                        while root_comment.parent_comment:
                            root_comment = root_comment.parent_comment
                        root_author = root_comment.user
                        print(f"[DEBUG] Root author: {root_author.id} ({root_author.username})")
                        if root_author != request.user:
                            ActionLogNotification.objects.create(
                                user=root_author,
                                action_log=action_log,
                                comment=comment
                            )
                            notified_user_ids.add(root_author.id)
                            print(f"[DEBUG] Notified root/original comment author: {root_author.id} ({root_author.username})")
                        else:
                            print(f"[DEBUG] Skipping root author notification - is sender")
                    except ActionLogComment.DoesNotExist:
                        print("[DEBUG] Parent comment does not exist for notification.")
                        pass

                print("\n=== Comment Creation Completed ===")
                print(f"Total users notified: {len(notified_user_ids)}")
                print(f"Notified user IDs: {notified_user_ids}")
                
                serializer = ActionLogCommentSerializer(comment)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            # GET method - return all comments
            print(f"Fetching comments for action log {pk}")
            
            # Get all comments for the log with their replies
            comments = ActionLogComment.objects.filter(
                action_log_id=pk,
                parent_comment=None  # Get only top-level comments
            ).select_related('user').prefetch_related(
                'replies',
                'replies__user'
            ).order_by('-created_at')
            
            print(f"Found {comments.count()} top-level comments")
            
            serializer = ActionLogCommentSerializer(comments, many=True)
            print(f"Serialized comments: {serializer.data}")
            return Response(serializer.data)

        except Exception as e:
            import traceback
            print(f"Error in comments view: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
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
            import traceback
            print(f"Error in mark_comments_viewed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        action_log = self.get_object()
        
        if not can_approve_action_log(request.user, action_log):
            return Response(
                {"detail": "You don't have permission to approve this action log"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            action_log.approve(request.user)
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
                request.user,
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
        print("\n=== Comment Creation Started ===")
        print(f"Request method: {self.request.method}")
        print(f"Request user: {self.request.user.id} ({self.request.user.username})")
        print(f"Request data: {self.request.data}")
        
        action_log_id = self.request.data.get('action_log')
        parent_id = self.request.data.get('parent_comment_id')
        
        print(f"Action log ID: {action_log_id}")
        print(f"Parent comment ID: {parent_id}")
        
        try:
            action_log = ActionLog.objects.get(id=action_log_id)
            print(f"Found action log: {action_log.id} - {action_log.title}")
            
            # Save the comment
            comment = serializer.save(user=self.request.user, action_log=action_log)
            print(f"Comment created with ID: {comment.id}")
            
            # Create notifications
            print("\n=== Creating Notifications ===")
            notified_user_ids = set()
            print(f"Sender user ID: {self.request.user.id}")
            
            # Create notification for assigned users
            assigned_users = action_log.assigned_to.all()
            print(f"Number of assigned users: {assigned_users.count()}")
            for user in assigned_users:
                print(f"Checking assigned user: {user.id} ({user.username})")
                if user != self.request.user:  # Don't notify the commenter
                    ActionLogNotification.objects.create(
                        user=user,
                        action_log=action_log,
                        comment=comment
                    )
                    notified_user_ids.add(user.id)
                    print(f"Notified assigned user: {user.id} ({user.username})")
                else:
                    print(f"Skipping notification for sender: {user.id} ({user.username})")

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
                    print(f"Notified assigned user: {user.id} ({user.username})")
                else:
                    print(f"Skipping notification for sender or already notified: {user.id} ({user.username})")

            # If this is a reply, notify the parent comment's author and root/original comment's author
            if parent_id:
                try:
                    parent_comment = ActionLogComment.objects.get(id=parent_id)
                    parent_author = parent_comment.user
                    print(f"[DEBUG] Parent author: {parent_author.id} ({parent_author.username})")
                    print(f"[DEBUG] Sender: {self.request.user.id} ({self.request.user.username})")
                    if parent_author != self.request.user and parent_author.id not in notified_user_ids:
                        ActionLogNotification.objects.create(
                            user=parent_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(parent_author.id)
                        print(f"[DEBUG] Notified parent comment author: {parent_author.id} ({parent_author.username})")
                    else:
                        print(f"[DEBUG] Skipping parent author notification - already notified or is sender")
                    # Traverse up to the root/original comment
                    root_comment = parent_comment
                    while root_comment.parent_comment:
                        root_comment = root_comment.parent_comment
                    root_author = root_comment.user
                    print(f"[DEBUG] Root author: {root_author.id} ({root_author.username})")
                    if root_author != self.request.user:
                        ActionLogNotification.objects.create(
                            user=root_author,
                            action_log=action_log,
                            comment=comment
                        )
                        notified_user_ids.add(root_author.id)
                        print(f"[DEBUG] Notified root/original comment author: {root_author.id} ({root_author.username})")
                    else:
                        print(f"[DEBUG] Skipping root author notification - is sender")
                except ActionLogComment.DoesNotExist:
                    print("[DEBUG] Parent comment does not exist for notification.")
                    pass

            print("\n=== Comment Creation Completed ===")
            print(f"Total users notified: {len(notified_user_ids)}")
            print(f"Notified user IDs: {notified_user_ids}")
            
        except ActionLog.DoesNotExist:
            print(f"Action log not found: {action_log_id}")
            raise Http404("Action log not found") 