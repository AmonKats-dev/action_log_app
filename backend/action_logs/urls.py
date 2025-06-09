from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActionLogViewSet

router = DefaultRouter()
router.register('', ActionLogViewSet, basename='action-log')

urlpatterns = [
    path('', include(router.urls)),
] 