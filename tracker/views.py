"""
API Views for CosmosTrace application.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Asteroid, CloseApproach, UserAsteroidWatch,
    AlertConfiguration, Notification, NotificationLog
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, AsteroidSerializer,
    UserAsteroidWatchSerializer, AlertConfigurationSerializer,
    NotificationSerializer, CloseApproachSerializer
)
from .tasks import send_notification_email


class UserRegistrationView(APIView):
    """User registration endpoint."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'User registered successfully'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile endpoint."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AsteroidViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for asteroid data."""
    queryset = Asteroid.objects.prefetch_related('close_approaches')
    serializer_class = AsteroidSerializer
    filterset_fields = ['is_potentially_hazardous', 'name']
    search_fields = ['name', 'nasa_id']
    ordering_fields = ['name', 'is_potentially_hazardous', 'last_updated']
    ordering = ['-is_potentially_hazardous', 'name']

    @action(detail=False, methods=['get'])
    def upcoming_approaches(self, request):
        """Get asteroids with upcoming close approaches."""
        days_ahead = int(request.query_params.get('days', 7))
        future_date = timezone.now() + timedelta(days=days_ahead)

        asteroids = Asteroid.objects.filter(
            close_approaches__approach_date__gte=timezone.now(),
            close_approaches__approach_date__lte=future_date
        ).distinct()

        serializer = self.get_serializer(asteroids, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def hazardous(self, request):
        """Get all hazardous asteroids."""
        asteroids = Asteroid.objects.filter(is_potentially_hazardous=True)
        serializer = self.get_serializer(asteroids, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def close_approaches(self, request, pk=None):
        """Get close approaches for a specific asteroid."""
        asteroid = self.get_object()
        approaches = asteroid.close_approaches.all().order_by('approach_date')
        serializer = CloseApproachSerializer(approaches, many=True)
        return Response(serializer.data)


class UserAsteroidWatchViewSet(viewsets.ModelViewSet):
    """ViewSet for user's watched asteroids."""
    serializer_class = UserAsteroidWatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAsteroidWatch.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        asteroid_id = request.data.get('asteroid_id')
        try:
            asteroid = Asteroid.objects.get(id=asteroid_id)
            watched, created = UserAsteroidWatch.objects.get_or_create(
                user=request.user,
                asteroid=asteroid
            )
            if created:
                return Response(
                    {'message': f'{asteroid.name} added to watched list'},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'message': f'{asteroid.name} is already in your watched list'},
                    status=status.HTTP_200_OK
                )
        except Asteroid.DoesNotExist:
            return Response(
                {'error': 'Asteroid not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        asteroid_name = instance.asteroid.name
        instance.delete()
        return Response(
            {'message': f'{asteroid_name} removed from watched list'},
            status=status.HTTP_204_NO_CONTENT
        )


class AlertConfigurationView(APIView):
    """View for managing alert configuration."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        config, created = AlertConfiguration.objects.get_or_create(user=request.user)
        serializer = AlertConfigurationSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        config, created = AlertConfiguration.objects.get_or_create(user=request.user)
        serializer = AlertConfigurationSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'notification_type']
    ordering_fields = ['created_at', 'scheduled_for']
    ordering = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read."""
        Notification.objects.filter(
            user=request.user,
            status__in=['pending', 'sent']
        ).update(status='read', read_at=timezone.now())
        return Response({'status': 'all notifications marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = Notification.objects.filter(
            user=request.user,
            status__in=['pending', 'sent']
        ).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming notifications."""
        notifications = self.get_queryset().filter(
            scheduled_for__gt=timezone.now()
        )[:10]
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)


class DashboardStatsView(APIView):
    """Dashboard statistics endpoint."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics."""
        upcoming_days = int(request.query_params.get('days', 7))
        future_date = timezone.now() + timedelta(days=upcoming_days)

        # Get statistics
        total_asteroids = Asteroid.objects.count()
        hazardous_asteroids = Asteroid.objects.filter(is_potentially_hazardous=True).count()
        
        upcoming_approaches = CloseApproach.objects.filter(
            approach_date__gte=timezone.now(),
            approach_date__lte=future_date
        ).count()

        user_watched = UserAsteroidWatch.objects.filter(user=request.user).count()
        unread_notifications = Notification.objects.filter(
            user=request.user,
            status__in=['pending', 'sent']
        ).count()

        # Get upcoming close approaches
        closest_approach = CloseApproach.objects.filter(
            approach_date__gte=timezone.now()
        ).order_by('miss_distance_km').first()

        return Response({
            'total_asteroids': total_asteroids,
            'hazardous_asteroids': hazardous_asteroids,
            'safe_asteroids': total_asteroids - hazardous_asteroids,
            'upcoming_approaches': upcoming_approaches,
            'user_watched_asteroids': user_watched,
            'unread_notifications': unread_notifications,
            'closest_approach': {
                'asteroid': closest_approach.asteroid.name if closest_approach else None,
                'approach_date': closest_approach.approach_date if closest_approach else None,
                'distance_km': closest_approach.miss_distance_km if closest_approach else None,
            } if closest_approach else None
        })
