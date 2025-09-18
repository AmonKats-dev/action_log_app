from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Role, LoginCode, Delegation
from .serializers import UserSerializer, RoleSerializer, DelegationSerializer
from .permissions import IsSuperAdminOrReadOnly, CanManageUsers
from notifications.services import SMSNotificationService
from datetime import timedelta
import logging
from django.db import models
from rest_framework import serializers

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Check if remember_me is requested
        remember_me = self.context.get('request').data.get('remember_me', False)
        
        if remember_me:
            # Extend token lifetime for remember me
            self.token_lifetime = timedelta(days=30)
            self.refresh_token_lifetime = timedelta(days=60)
        
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class SendLoginCodeView(APIView):
    """Send SMS verification code to phone number"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response(
                {"error": "Phone number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists with this phone number
        try:
            user = User.objects.get(phone_number=phone_number, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "No active user found with this phone number"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate and save login code
        try:
            login_code = LoginCode.create_for_phone(phone_number)
            
            # Check if we're in test mode (no Twilio credentials or DEBUG mode)
            from django.conf import settings
            is_test_mode = (
                not getattr(settings, 'TWILIO_ACCOUNT_SID', None) or 
                not getattr(settings, 'TWILIO_AUTH_TOKEN', None) or 
                settings.DEBUG
            )
            
            if is_test_mode:
                # Test mode - return the code directly
                logger.info(f"TEST MODE: Login code for {phone_number}: {login_code.code}")
                return Response({
                    "message": "Verification code sent successfully (TEST MODE)",
                    "test_code": login_code.code,
                    "is_test_mode": True
                }, status=status.HTTP_200_OK)
            else:
                # Production mode - send real SMS
                sms_service = SMSNotificationService()
                message = f"Your Action Log System login code is: {login_code.code}. Valid for 10 minutes."
                
                if sms_service.send_notification(phone_number, message):
                    logger.info(f"Login code sent successfully to {phone_number}")
                    return Response(
                        {"message": "Verification code sent successfully"},
                        status=status.HTTP_200_OK
                    )
                else:
                    # Delete the code if SMS failed
                    login_code.delete()
                    return Response(
                        {"error": "Failed to send verification code. Please try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
        except Exception as e:
            logger.error(f"Error sending login code to {phone_number}: {str(e)}")
            return Response(
                {"error": "Failed to send verification code. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyLoginCodeView(APIView):
    """Verify SMS code and return JWT tokens"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        
        print(f"DEBUG: Verifying login code for phone: {phone_number}")
        print(f"DEBUG: Code provided: {code}")
        
        if not phone_number or not code:
            return Response(
                {"error": "Phone number and code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the user
        try:
            user = User.objects.get(phone_number=phone_number, is_active=True)
            print(f"DEBUG: Found user: {user.username}")
        except User.DoesNotExist:
            return Response(
                {"error": "No active user found with this phone number"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify the code
        try:
            login_code = LoginCode.objects.get(
                phone_number=phone_number,
                code=code,
                is_used=False
            )
            
            if login_code.is_expired():
                return Response(
                    {"error": "Verification code has expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark code as used
            login_code.is_used = True
            login_code.save()
            
            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            print(f"DEBUG: Generated access token: {access_token[:50]}...")
            print(f"DEBUG: Generated refresh token: {refresh_token[:50]}...")
            
            response_data = {
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            }
            
            print(f"DEBUG: Response data keys: {response_data.keys()}")
            
            return Response(response_data)
            
        except LoginCode.DoesNotExist:
            return Response(
                {"error": "Invalid verification code"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error verifying login code for {phone_number}: {str(e)}")
            return Response(
                {"error": "Failed to verify code. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperAdminOrReadOnly]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        
        # Get filters from query params
        department_id = self.request.query_params.get('department')
        department_unit_id = self.request.query_params.get('department_unit')
        
        print(f"Request from user {user.username} (dept: {user.department_id})")
        print(f"Filters - department: {department_id}, unit: {department_unit_id}")
        
        # Apply department filter if specified
        if department_id:
            queryset = queryset.filter(department_id=department_id)
            print(f"Filtered queryset by department {department_id}")
        
        # Apply department unit filter if specified
        if department_unit_id:
            queryset = queryset.filter(department_unit_id=department_unit_id)
            print(f"Filtered queryset by department unit {department_unit_id}")
        
        # Apply role-based filtering
        if hasattr(user, 'is_super_admin') and user.is_super_admin:
            print(f"User {user.username} is super admin, returning all users")
            return queryset
        elif hasattr(user, 'role') and user.role and user.role.can_view_all_users:
            # Commissioner and Assistant Commissioner can view all users
            print(f"User {user.username} has view_all_users permission")
            return queryset
        elif hasattr(user, 'department_unit') and user.department_unit:
            # Department unit head can only view users in their unit
            print(f"User {user.username} is department unit head, filtering by unit {user.department_unit_id}")
            return queryset.filter(department_unit=user.department_unit)
        else:
            # For other roles, they can only see users in their department
            print(f"User {user.username} is regular user, filtering by department {user.department_id}")
            return queryset.filter(department=user.department)

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        
        # Check if user has permission to assign to commissioner
        if data.get('role') and data['role'].name == 'commissioner':
            if not (user.role and user.role.can_assign_to_commissioner):
                raise permissions.PermissionDenied("You don't have permission to assign commissioner role")
        
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        
        # Check if user has permission to assign to commissioner
        if data.get('role') and data['role'].name == 'commissioner':
            if not (user.role and user.role.can_assign_to_commissioner):
                raise permissions.PermissionDenied("You don't have permission to assign commissioner role")
        
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def test_auth(self, request):
        """Test endpoint to verify JWT authentication"""
        print(f"DEBUG: Test auth endpoint called")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request user: {request.user}")
        print(f"DEBUG: User is authenticated: {request.user.is_authenticated}")
        print(f"DEBUG: Authorization header: {request.headers.get('Authorization', 'NOT FOUND')}")
        print(f"DEBUG: HTTP_AUTHORIZATION: {request.META.get('HTTP_AUTHORIZATION', 'NOT FOUND')}")
        
        # Test JWT token validation
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            print(f"DEBUG: Token received: {token[:50]}...")
            
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from rest_framework_simplejwt.exceptions import TokenError
                
                # Try to validate the token
                access_token = AccessToken(token)
                print(f"DEBUG: Token is valid, user_id: {access_token['user_id']}")
                
                return Response({
                    "message": "Token is valid",
                    "user_id": access_token['user_id'],
                    "token_type": access_token['token_type'],
                    "exp": access_token['exp']
                })
            except TokenError as e:
                print(f"DEBUG: Token validation failed: {str(e)}")
                return Response({
                    "message": "Token validation failed",
                    "error": str(e)
                })
        
        if request.user.is_authenticated:
            return Response({
                "message": "Authentication working",
                "user": request.user.username,
                "user_id": request.user.id
            })
        else:
            return Response({
                "message": "Not authenticated",
                "headers": dict(request.headers)
            })

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        try:
            # Debug: Log the request headers and user
            print(f"DEBUG: Request headers: {dict(request.headers)}")
            print(f"DEBUG: Request user: {request.user}")
            print(f"DEBUG: User is authenticated: {request.user.is_authenticated}")
            print(f"DEBUG: Authorization header: {request.headers.get('Authorization', 'NOT FOUND')}")
            print(f"DEBUG: HTTP_AUTHORIZATION: {request.META.get('HTTP_AUTHORIZATION', 'NOT FOUND')}")
            
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG: Error in me endpoint: {str(e)}")
            return Response(
                {"error": "Failed to fetch user profile"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def department_users(self, request):
        """Get users by department"""
        department_id = request.query_params.get('department')
        
        if department_id:
            # If department parameter is provided, filter by that department
            try:
                users = User.objects.filter(department_id=department_id)
            except ValueError:
                return Response(
                    {"error": "Invalid department ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # If no department parameter, use current user's department
            if not request.user.department:
                return Response(
                    {"error": "User is not assigned to any department"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            users = User.objects.filter(department=request.user.department)
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def department_unit_users(self, request):
        """Get users by department unit"""
        department_unit_id = request.query_params.get('department_unit')
        
        if department_unit_id:
            # If department_unit parameter is provided, filter by that unit
            try:
                users = User.objects.filter(department_unit_id=department_unit_id)
            except ValueError:
                return Response(
                    {"error": "Invalid department unit ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # If no department_unit parameter, use current user's department unit
            if not request.user.department_unit:
                return Response(
                    {"error": "User is not assigned to any department unit"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            users = User.objects.filter(department_unit=request.user.department_unit)
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

class DelegationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delegations"""
    queryset = Delegation.objects.all()
    serializer_class = DelegationSerializer
    permission_classes = [permissions.IsAuthenticated]
    

    
    def get_queryset(self):
        user = self.request.user
        
        # Commissioner, super admin, and Ag. C/PAP users can see all delegations
        if user.is_commissioner or user.is_super_admin or user.can_manage_delegations():
            return Delegation.objects.all().order_by('-delegated_at', '-id')
        
        # Other users can only see delegations they're involved in
        return Delegation.objects.filter(
            models.Q(delegated_by=user) | models.Q(delegated_to=user)
        ).order_by('-delegated_at', '-id')
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # Debug: Print the data being received
        print(f"DEBUG: Creating delegation for user {user.username} (ID: {user.id})")
        print(f"DEBUG: Request data: {self.request.data}")
        print(f"DEBUG: Validated data: {serializer.validated_data}")
        
        print(f"DEBUG: User designation: '{user.designation}'")
        print(f"DEBUG: Can manage delegations: {user.can_manage_delegations()}")
        
        # Allow commissioners, super admins, and Ag. C/PAP users to create delegations
        if not (user.is_commissioner or user.is_super_admin or user.can_manage_delegations()):
            raise permissions.PermissionDenied("Only commissioners and Ag. C/PAP users can create delegations")
        
        # Check if delegation already exists
        delegated_to_id = serializer.validated_data.get('delegated_to_id')
        
        # Get the target user to check delegation restrictions
        try:
            target_user = User.objects.get(id=delegated_to_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Target user does not exist")
        
        # Check if current user can delegate to the target user
        if not user.can_delegate_to_user(target_user):
            if user.has_ag_acpap_designation():
                raise permissions.PermissionDenied("Ag. AC/PAP users cannot create delegations - they need delegation from Ag. C/PAP users")
            else:
                raise permissions.PermissionDenied("You cannot delegate to this user")
        
        # For Ag. C/PAP users: Check if they already have an active delegation
        if user.has_ag_cpap_designation():
            existing_active_delegation = Delegation.objects.filter(
                delegated_by=user,
                is_active=True
            ).first()
            
            if existing_active_delegation:
                # Automatically revoke the existing delegation
                existing_active_delegation.is_active = False
                existing_active_delegation.save()
                print(f"DEBUG: Automatically revoked existing delegation {existing_active_delegation.id} for Ag. C/PAP user")
        
        # Check if delegation already exists to the same user
        existing_delegation = Delegation.objects.filter(
            delegated_by=user,
            delegated_to_id=delegated_to_id
        ).first()
        
        if existing_delegation:
            print(f"DEBUG: Delegation already exists: {existing_delegation}")
            if existing_delegation.is_active:
                # For Ag. C/PAP users, this should not happen due to the above check
                # For other users, raise an error
                if not user.has_ag_cpap_designation():
                    raise serializers.ValidationError(
                        f"A delegation to this user already exists and is active. "
                        f"Please revoke the existing delegation first."
                    )
            else:
                # Reactivate the existing delegation
                existing_delegation.is_active = True
                existing_delegation.expires_at = serializer.validated_data.get('expires_at')
                existing_delegation.reason = serializer.validated_data.get('reason')
                existing_delegation.save()
                print(f"DEBUG: Reactivated existing delegation: {existing_delegation}")
                return existing_delegation
        
        # For non-Ag. C/PAP users: Automatically deactivate any existing active delegations
        if not user.has_ag_cpap_designation():
            active_delegations = Delegation.objects.filter(
                delegated_by=user,
                is_active=True
            )
            if active_delegations.exists():
                print(f"DEBUG: Deactivating {active_delegations.count()} existing active delegations")
                active_delegations.update(is_active=False)
        
        # Set the delegated_by to the current user
        delegation = serializer.save(delegated_by=user)
        print(f"DEBUG: Created new delegation: {delegation}")
        return delegation
    
    def destroy(self, request, *args, **kwargs):
        """Delete a delegation - only super admins can delete"""
        user = request.user
        
        if not user.is_super_admin:
            raise permissions.PermissionDenied("Only super admins can delete delegations")
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a delegation"""
        delegation = self.get_object()
        user = request.user
        
        # Only the commissioner/Ag. C/PAP who created the delegation can revoke it
        if delegation.delegated_by != user and not user.is_super_admin:
            raise permissions.PermissionDenied("You can only revoke your own delegations")
        
        # Only commissioners, Ag. C/PAP, and super admins can revoke
        if not (user.is_commissioner or user.is_super_admin or user.can_manage_delegations()):
            raise permissions.PermissionDenied("Only commissioners and Ag. C/PAP users can revoke delegations")
        
        delegation.is_active = False
        delegation.save()
        
        return Response({'message': 'Delegation revoked successfully'})
    
    @action(detail=False, methods=['get'])
    def my_delegations(self, request):
        """Get delegations for the current user"""
        user = request.user
        
        if user.is_commissioner or user.is_super_admin or user.can_manage_delegations():
            # Commissioners and Ag. C/PAP users see delegations they've given
            delegations = Delegation.objects.filter(delegated_by=user).order_by('-delegated_at', '-id')
        else:
            # Other users see delegations they've received
            delegations = Delegation.objects.filter(delegated_to=user, is_active=True).order_by('-delegated_at', '-id')
        
        serializer = self.get_serializer(delegations, many=True)
        return Response(serializer.data) 