"""
URL Configuration for CosmosTrace project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .health import health_check
from tracker.auth_views import login_view, register_view, me_view, logout_view

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    
    # Custom auth endpoints
    path('api/auth/login/', login_view, name='auth_login'),
    path('api/auth/register/', register_view, name='auth_register'),
    path('api/auth/me/', me_view, name='auth_me'),
    path('api/auth/logout/', logout_view, name='auth_logout'),
    
    # JWT token endpoints
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('api/', include('tracker.urls')),
]
