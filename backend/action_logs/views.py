from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ActionLog, ActionLogComment, ActionLogAssignmentHistory
from .serializers import ActionLogSerializer, ActionLogApprovalSerializer, ActionLogAssignmentHistorySerializer
from users.permissions import can_approve_action_log

class ActionLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role.name in ['commissioner', 'super_admin']:
            return ActionLog.objects.all()
        return ActionLog.objects.filter(department=user.department)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
        response = super().update(request, *args, **kwargs)
        
        # If there's a comment and it's not an assignment update, create a new comment record
        if comment_text and 'assigned_to' not in request.data:
            ActionLogComment.objects.create(
                action_log=instance,
                user=request.user,
                comment=comment_text
            )
        
        return response

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get all comments for an action log or create a new comment"""
        try:
            print(f"Fetching comments for action log {pk}")
            action_log = self.get_object()
            print(f"Found action log: {action_log}")
            
            if request.method == 'POST':
                comment_text = request.data.get('comment')
                parent_comment_id = request.data.get('parent_comment_id')
                
                if not comment_text:
                    return Response(
                        {"detail": "Comment text is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                parent_comment = None
                if parent_comment_id:
                    try:
                        parent_comment = ActionLogComment.objects.get(
                            id=parent_comment_id,
                            action_log=action_log
                        )
                    except ActionLogComment.DoesNotExist:
                        return Response(
                            {"detail": "Parent comment not found"},
                            status=status.HTTP_404_NOT_FOUND
                        )
                
                comment = ActionLogComment.objects.create(
                    action_log=action_log,
                    user=request.user,
                    comment=comment_text,
                    parent_comment=parent_comment
                )
                
                return Response({
                    'id': comment.id,
                    'comment': comment.comment,
                    'user': {
                        'id': comment.user.id,
                        'first_name': comment.user.first_name,
                        'last_name': comment.user.last_name,
                        'email': comment.user.email
                    },
                    'created_at': comment.created_at,
                    'updated_at': comment.updated_at,
                    'status': action_log.status,
                    'is_approved': action_log.approved_by is not None,
                    'parent_comment_id': parent_comment.id if parent_comment else None
                }, status=status.HTTP_201_CREATED)
            
            # GET method
            print("Fetching top-level comments")
            try:
                comments = action_log.comments.filter(parent_comment__isnull=True).select_related('user')
                print(f"Found {comments.count()} top-level comments")
                for comment in comments:
                    print(f"Comment {comment.id}: user={comment.user}, parent={comment.parent_comment}")
            except Exception as e:
                print(f"Error fetching comments: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                raise
            
            def format_comment(comment):
                try:
                    print(f"Formatting comment {comment.id}")
                    if not comment.user:
                        print(f"Warning: Comment {comment.id} has no user")
                        return None
                        
                    user_data = {
                        'id': comment.user.id,
                        'first_name': comment.user.first_name or '',
                        'last_name': comment.user.last_name or '',
                        'email': comment.user.email or ''
                    }
                    print(f"User data: {user_data}")
                    
                    try:
                        replies = comment.replies.all().select_related('user')
                        print(f"Found {replies.count()} replies for comment {comment.id}")
                    except Exception as e:
                        print(f"Error fetching replies for comment {comment.id}: {str(e)}")
                        replies = []
                    
                    formatted_replies = []
                    for reply in replies:
                        try:
                            formatted_reply = format_comment(reply)
                            if formatted_reply:
                                formatted_replies.append(formatted_reply)
                        except Exception as e:
                            print(f"Error formatting reply {reply.id}: {str(e)}")
                    
                    print(f"Formatted {len(formatted_replies)} replies for comment {comment.id}")
                    
                    return {
                        'id': comment.id,
                        'comment': comment.comment,
                        'user': user_data,
                        'created_at': comment.created_at,
                        'updated_at': comment.updated_at,
                        'status': action_log.status,
                        'is_approved': action_log.approved_by is not None,
                        'replies': formatted_replies
                    }
                except Exception as e:
                    print(f"Error formatting comment {comment.id}: {str(e)}")
                    print(f"Comment data: {comment.__dict__}")
                    return None
            
            print("Formatting all comments")
            formatted_comments = []
            for comment in comments:
                try:
                    formatted = format_comment(comment)
                    if formatted:
                        formatted_comments.append(formatted)
                except Exception as e:
                    print(f"Error processing comment {comment.id}: {str(e)}")
            
            print(f"Successfully formatted {len(formatted_comments)} comments")
            return Response(formatted_comments)
        except Exception as e:
            print(f"Error in comments endpoint: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
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
            print(f"Fetching assignment history for action log {pk}")
            action_log = self.get_object()
            print(f"Found action log: {action_log}")
            
            # Log the action log's assignment history relationship
            print(f"Action log assignment_history relationship: {action_log.assignment_history}")
            
            # Get history records with optimized queries
            history = (
                action_log.assignment_history
                .select_related('assigned_by')
                .prefetch_related('assigned_to')
                .order_by('-assigned_at')
            )
            print(f"Found {history.count()} history records")
            
            # Log each history record
            for record in history:
                print(f"History record: id={record.id}, assigned_by={record.assigned_by}, assigned_at={record.assigned_at}")
                print(f"Assigned to users: {[user.id for user in record.get_assigned_to_users()]}")
            
            # Serialize the data
            serializer = ActionLogAssignmentHistorySerializer(history, many=True)
            serialized_data = serializer.data
            print(f"Serialized data: {serialized_data}")
            
            return Response(serialized_data)
        except Exception as e:
            print(f"Error in assignment_history endpoint: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 