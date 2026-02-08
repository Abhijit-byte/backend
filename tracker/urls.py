"""
URL Configuration for CosmosTrace Tracker API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegistrationView, UserProfileView, AsteroidViewSet,
    UserAsteroidWatchViewSet, AlertConfigurationView,
    NotificationViewSet, DashboardStatsView
)

router = DefaultRouter()
router.register(r'asteroids', AsteroidViewSet)
router.register(r'watched-asteroids', UserAsteroidWatchViewSet, basename='watched-asteroids')
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    # User Management
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Alert Configuration
    path('alerts/config/', AlertConfigurationView.as_view(), name='alert-config'),
    
    # Dashboard
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Router URLs
    path('', include(router.urls)),
]
