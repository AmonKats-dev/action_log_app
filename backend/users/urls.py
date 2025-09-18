from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RoleViewSet, DelegationViewSet, SendLoginCodeView, VerifyLoginCodeView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'delegations', DelegationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Use separate API views for login endpoints to avoid permission conflicts
    path('send_login_code/', SendLoginCodeView.as_view(), name='send_login_code'),
    path('verify_login_code/', VerifyLoginCodeView.as_view(), name='verify_login_code'),
    # Keep the me endpoint in UserViewSet since it requires authentication
    path('me/', UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('test_auth/', UserViewSet.as_view({'get': 'test_auth'}), name='test_auth'),
    # Add department-related endpoints
    path('department_users/', UserViewSet.as_view({'get': 'department_users'}), name='department-users'),
    path('department_unit_users/', UserViewSet.as_view({'get': 'department_unit_users'}), name='department-unit-users'),
] 