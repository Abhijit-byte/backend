"""
DRF Serializers for CosmosTrace API.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Asteroid, CloseApproach, UserAsteroidWatch,
    AlertConfiguration, Notification, NotificationLog
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        AlertConfiguration.objects.create(user=user)
        return user


class CloseApproachSerializer(serializers.ModelSerializer):
    """Serializer for close approach data."""
    class Meta:
        model = CloseApproach
        fields = [
            'id', 'approach_date', 'miss_distance_km', 'miss_distance_miles',
            'miss_distance_lunar', 'relative_velocity_kmps', 'relative_velocity_kmph',
            'relative_velocity_mph', 'orbiting_body'
        ]
        read_only_fields = ['id']


class AsteroidSerializer(serializers.ModelSerializer):
    """Serializer for asteroid data."""
    close_approaches = CloseApproachSerializer(many=True, read_only=True)
    upcoming_approaches = serializers.SerializerMethodField()

    class Meta:
        model = Asteroid
        fields = [
            'id', 'nasa_id', 'name', 'diameter_min', 'diameter_max',
            'absolute_magnitude', 'is_potentially_hazardous', 'nasa_url',
            'orbital_period', 'semi_major_axis', 'eccentricity',
            'close_approaches', 'upcoming_approaches', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']

    def get_upcoming_approaches(self, obj):
        """Get only upcoming close approaches."""
        upcoming = obj.close_approaches.filter(approach_date__gt=timezone.now()).order_by('approach_date')[:5]
        return CloseApproachSerializer(upcoming, many=True).data


class UserAsteroidWatchSerializer(serializers.ModelSerializer):
    """Serializer for watched asteroids."""
    asteroid = AsteroidSerializer(read_only=True)
    asteroid_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserAsteroidWatch
        fields = ['id', 'asteroid', 'asteroid_id', 'watched_since', 'notes']
        read_only_fields = ['id', 'watched_since']


class AlertConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for alert configuration."""
    class Meta:
        model = AlertConfiguration
        fields = [
            'id', 'alert_type', 'min_distance_km', 'max_distance_km',
            'min_velocity_kmps', 'min_days_notice', 'notification_method',
            'hazard_only', 'enabled', 'updated_at'
        ]
        read_only_fields = ['id']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    asteroid_name = serializers.CharField(source='close_approach.asteroid.name', read_only=True)
    approach_date = serializers.DateTimeField(source='close_approach.approach_date', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'status',
            'asteroid_name', 'approach_date', 'scheduled_for', 'read_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs."""
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'message', 'delivery_method',
            'success', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Import timezone for getting upcoming approaches
from django.utils import timezone
