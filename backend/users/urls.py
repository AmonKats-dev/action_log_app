from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RoleViewSet

router = DefaultRouter()
router.register(r'roles', RoleViewSet)
router.register(r'', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 