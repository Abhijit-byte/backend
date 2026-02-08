"""
Database models for CosmosTrace tracker app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from django.utils import timezone

# Import JWT token models
from .jwt_models import (
    RefreshToken,
    AccessToken, 
    LoginSession,
    UserProfile
)


class Asteroid(models.Model):
    """Model to store asteroid data from NASA API."""
    nasa_id = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    diameter_min = models.FloatField(null=True, blank=True)  # meters
    diameter_max = models.FloatField(null=True, blank=True)  # meters
    absolute_magnitude = models.FloatField(null=True, blank=True)
    is_potentially_hazardous = models.BooleanField(default=False, db_index=True)
    nasa_url = models.URLField(null=True, blank=True)
    orbital_period = models.FloatField(null=True, blank=True)  # days
    semi_major_axis = models.FloatField(null=True, blank=True)  # AU
    eccentricity = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_potentially_hazardous', 'name']
        indexes = [
            models.Index(fields=['is_potentially_hazardous']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} (ID: {self.nasa_id})"


class CloseApproach(models.Model):
    """Model to store close approach events."""
    asteroid = models.ForeignKey(Asteroid, on_delete=models.CASCADE, related_name='close_approaches')
    approach_date = models.DateTimeField(db_index=True)
    miss_distance_km = models.FloatField()
    miss_distance_miles = models.FloatField(null=True, blank=True)
    miss_distance_lunar = models.FloatField(null=True, blank=True)
    relative_velocity_kmps = models.FloatField()  # km per second
    relative_velocity_kmph = models.FloatField(null=True, blank=True)
    relative_velocity_mph = models.FloatField(null=True, blank=True)
    orbiting_body = models.CharField(max_length=50, default='Earth')
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['approach_date']
        indexes = [
            models.Index(fields=['approach_date']),
            models.Index(fields=['asteroid', 'approach_date']),
        ]
        unique_together = [['asteroid', 'approach_date']]

    def __str__(self):
        return f"{self.asteroid.name} - {self.approach_date.date()}"

    def is_upcoming(self):
        """Check if approach is in the future."""
        return self.approach_date > timezone.now()

    def days_until_approach(self):
        """Calculate days until approach."""
        if self.is_upcoming():
            delta = self.approach_date - timezone.now()
            return delta.days
        return 0


class UserAsteroidWatch(models.Model):
    """Model to track user's watched asteroids."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_asteroids')
    asteroid = models.ForeignKey(Asteroid, on_delete=models.CASCADE)
    watched_since = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [['user', 'asteroid']]

    def __str__(self):
        return f"{self.user.username} watching {self.asteroid.name}"


class AlertConfiguration(models.Model):
    """Model to store user's custom alert preferences."""
    ALERT_TYPES = [
        ('distance', 'Distance-based Alert'),
        ('hazard', 'Hazardous Asteroid Alert'),
        ('velocity', 'High Velocity Alert'),
        ('all', 'All Asteroids'),
    ]

    NOTIFICATION_METHODS = [
        ('email', 'Email'),
        ('dashboard', 'Dashboard Notification'),
        ('both', 'Both Email and Dashboard'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='alert_config')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='distance')
    min_distance_km = models.FloatField(
        default=10000000,
        validators=[MinValueValidator(0)],
        help_text="Alert only for asteroids closer than this (km)"
    )
    max_distance_km = models.FloatField(
        default=100000000,
        validators=[MinValueValidator(0)],
        help_text="Alert only for asteroids within this distance (km)"
    )
    min_velocity_kmps = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Alert for asteroids faster than this (km/s)"
    )
    min_days_notice = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Alert this many days before approach"
    )
    notification_method = models.CharField(
        max_length=20,
        choices=NOTIFICATION_METHODS,
        default='both'
    )
    hazard_only = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Alert Config for {self.user.username}"


class Notification(models.Model):
    """Model to store notifications."""
    NOTIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    close_approach = models.ForeignKey(CloseApproach, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='alert')
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS, default='pending')
    read_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['scheduled_for']),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

    def mark_as_read(self):
        """Mark notification as read."""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()

    def mark_as_sent(self):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()


class NotificationLog(models.Model):
    """Log of all notification attempts for auditing."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_logs')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    delivery_method = models.CharField(max_length=50)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for {self.user.username} at {self.created_at}"