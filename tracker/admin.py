"""
Django admin interface configuration for tracker app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Asteroid, CloseApproach, UserAsteroidWatch,
    AlertConfiguration, Notification, NotificationLog
)


@admin.register(Asteroid)
class AsteroidAdmin(admin.ModelAdmin):
    list_display = ['name', 'nasa_id', 'hazard_badge', 'diameter_max', 'last_updated']
    list_filter = ['is_potentially_hazardous', 'last_updated']
    search_fields = ['name', 'nasa_id']
    readonly_fields = ['nasa_id', 'created_at', 'last_updated']
    fieldsets = (
        ('Basic Information', {
            'fields': ('nasa_id', 'name', 'nasa_url')
        }),
        ('Physical Properties', {
            'fields': ('diameter_min', 'diameter_max', 'absolute_magnitude')
        }),
        ('Orbital Data', {
            'fields': ('orbital_period', 'semi_major_axis', 'eccentricity')
        }),
        ('Hazard Classification', {
            'fields': ('is_potentially_hazardous',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

    def hazard_badge(self, obj):
        if obj.is_potentially_hazardous:
            return format_html(
                '<span style="background-color: #ff6b6b; color: white; padding: 3px 10px; border-radius: 3px;">HAZARDOUS</span>'
            )
        return format_html(
            '<span style="background-color: #51cf66; color: white; padding: 3px 10px; border-radius: 3px;">SAFE</span>'
        )
    hazard_badge.short_description = 'Hazard Status'


@admin.register(CloseApproach)
class CloseApproachAdmin(admin.ModelAdmin):
    list_display = ['asteroid', 'approach_date', 'miss_distance_km', 'relative_velocity_kmps', 'is_upcoming']
    list_filter = ['approach_date', 'asteroid__is_potentially_hazardous']
    search_fields = ['asteroid__name']
    readonly_fields = ['created_at', 'last_updated']
    date_hierarchy = 'approach_date'
    fieldsets = (
        ('Asteroid & Date', {
            'fields': ('asteroid', 'approach_date')
        }),
        ('Distance Data', {
            'fields': ('miss_distance_km', 'miss_distance_miles', 'miss_distance_lunar')
        }),
        ('Velocity Data', {
            'fields': ('relative_velocity_kmps', 'relative_velocity_kmph', 'relative_velocity_mph')
        }),
        ('Additional', {
            'fields': ('orbiting_body', 'created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )

    def is_upcoming(self, obj):
        if obj.is_upcoming():
            return format_html('<span style="color: #51cf66;">Upcoming</span>')
        return format_html('<span style="color: #868e96;">Past</span>')
    is_upcoming.short_description = 'Status'


@admin.register(UserAsteroidWatch)
class UserAsteroidWatchAdmin(admin.ModelAdmin):
    list_display = ['user', 'asteroid', 'watched_since']
    list_filter = ['watched_since']
    search_fields = ['user__username', 'asteroid__name']
    readonly_fields = ['watched_since']


@admin.register(AlertConfiguration)
class AlertConfigurationAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'enabled', 'notification_method']
    list_filter = ['alert_type', 'enabled', 'notification_method']
    search_fields = ['user__username']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Alert Settings', {
            'fields': ('alert_type', 'hazard_only', 'enabled')
        }),
        ('Distance Parameters', {
            'fields': ('min_distance_km', 'max_distance_km')
        }),
        ('Velocity Parameters', {
            'fields': ('min_velocity_kmps',)
        }),
        ('Notification Settings', {
            'fields': ('min_days_notice', 'notification_method')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status_badge', 'scheduled_for', 'created_at']
    list_filter = ['status', 'notification_type', 'created_at']
    search_fields = ['user__username', 'title']
    readonly_fields = ['created_at', 'sent_at', 'read_at']
    date_hierarchy = 'created_at'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffd43b',
            'sent': '#51cf66',
            'failed': '#ff6b6b',
            'read': '#868e96'
        }
        color = colors.get(obj.status, '#868e96')
        return format_html(
            f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 3px;">{obj.status.upper()}</span>'
        )
    status_badge.short_description = 'Status'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'delivery_method', 'success', 'created_at']
    list_filter = ['success', 'delivery_method', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
