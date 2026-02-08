"""
Celery tasks for CosmosTrace application.
Handles periodic data fetching, alerts, and notifications.
"""
import requests
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

from .models import (
    Asteroid, CloseApproach, Notification,
    AlertConfiguration, UserAsteroidWatch, NotificationLog
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fetch_asteroids_data(self):
    """
    Fetch asteroid data from NASA API and update database.
    """
    try:
        nasa_api_key = settings.NASA_API_KEY
        base_url = settings.NASA_BASE_URL
        
        # Get date range (next 7 days)
        today = timezone.now().date()
        end_date = today + timedelta(days=7)
        
        url = f"{base_url}/feed?start_date={today}&end_date={end_date}&api_key={nasa_api_key}"
        
        logger.info(f"Fetching asteroid data from NASA API: {today} to {end_date}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        neo_feed = data.get('near_earth_objects', {})
        
        asteroids_created = 0
        approaches_created = 0
        
        # Process each date's asteroids
        for date_str, asteroids_list in neo_feed.items():
            for asteroid_data in asteroids_list:
                try:
                    # Create or get asteroid
                    asteroid, created = Asteroid.objects.get_or_create(
                        nasa_id=asteroid_data['id'],
                        defaults={
                            'name': asteroid_data['name'],
                            'diameter_min': asteroid_data.get('estimated_diameter', {}).get('meters', {}).get('estimated_diameter_min'),
                            'diameter_max': asteroid_data.get('estimated_diameter', {}).get('meters', {}).get('estimated_diameter_max'),
                            'absolute_magnitude': asteroid_data.get('absolute_magnitude_h'),
                            'is_potentially_hazardous': asteroid_data.get('is_potentially_hazardous_asteroid', False),
                            'nasa_url': asteroid_data.get('nasa_jpl_url'),
                        }
                    )
                    
                    if created:
                        asteroids_created += 1
                    
                    # Process close approaches
                    for approach_data in asteroid_data.get('close_approach_data', []):
                        approach_date = timezone.datetime.fromisoformat(
                            approach_data['close_approach_date'] + 'T00:00:00Z'
                        ).replace(tzinfo=timezone.utc)
                        
                        close_approach, created = CloseApproach.objects.get_or_create(
                            asteroid=asteroid,
                            approach_date=approach_date,
                            defaults={
                                'miss_distance_km': float(approach_data['miss_distance']['kilometers']),
                                'miss_distance_miles': float(approach_data['miss_distance']['miles']),
                                'miss_distance_lunar': float(approach_data['miss_distance']['lunar_distance']),
                                'relative_velocity_kmps': float(approach_data['relative_velocity']['kilometers_per_second']),
                                'relative_velocity_kmph': float(approach_data['relative_velocity']['kilometers_per_hour']),
                                'relative_velocity_mph': float(approach_data['relative_velocity']['miles_per_hour']),
                                'orbiting_body': approach_data.get('orbiting_body', 'Earth'),
                            }
                        )
                        
                        if created:
                            approaches_created += 1
                
                except Exception as e:
                    logger.error(f"Error processing asteroid {asteroid_data.get('name')}: {str(e)}")
                    continue
        
        logger.info(f"Asteroid data fetch complete: {asteroids_created} new asteroids, {approaches_created} new approaches")
        return {
            'status': 'success',
            'asteroids_created': asteroids_created,
            'approaches_created': approaches_created
        }
    
    except Exception as exc:
        logger.error(f"Error fetching asteroid data: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def check_and_notify_close_approaches(self):
    """
    Check for upcoming close approaches and create notifications.
    """
    try:
        logger.info("Checking for close approaches to notify...")
        
        # Get all active alert configurations
        alert_configs = AlertConfiguration.objects.filter(enabled=True)
        
        for config in alert_configs:
            user = config.user
            
            # Get upcoming close approaches
            min_date = timezone.now()
            max_date = timezone.now() + timedelta(days=config.min_days_notice)
            
            approaches = CloseApproach.objects.filter(
                approach_date__gte=min_date,
                approach_date__lte=max_date,
                asteroid__is_potentially_hazardous=True if config.hazard_only else True
            ).select_related('asteroid')
            
            # Filter based on user's watched asteroids if any
            watched_asteroid_ids = UserAsteroidWatch.objects.filter(
                user=user
            ).values_list('asteroid_id', flat=True)
            
            if watched_asteroid_ids:
                approaches = approaches.filter(asteroid_id__in=watched_asteroid_ids)
            
            # Filter based on distance and velocity
            approaches = approaches.filter(
                miss_distance_km__gte=config.min_distance_km,
                miss_distance_km__lte=config.max_distance_km,
                relative_velocity_kmps__gte=config.min_velocity_kmps
            )
            
            # Create notifications for new approaches
            for approach in approaches:
                notification, created = Notification.objects.get_or_create(
                    user=user,
                    close_approach=approach,
                    defaults={
                        'title': f"Alert: {approach.asteroid.name} approaching Earth",
                        'message': f"{approach.asteroid.name} will be {approach.miss_distance_km:,.0f} km from Earth on {approach.approach_date.strftime('%Y-%m-%d')}. Velocity: {approach.relative_velocity_kmps:.2f} km/s",
                        'notification_type': 'alert',
                        'scheduled_for': timezone.now(),
                    }
                )
                
                if created:
                    logger.info(f"Created notification for {user.username}: {approach.asteroid.name}")
        
        return {'status': 'success', 'message': 'Close approach check completed'}
    
    except Exception as e:
        logger.error(f"Error checking close approaches: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def send_pending_notifications(self):
    """
    Send pending notifications to users via email and dashboard.
    """
    try:
        logger.info("Sending pending notifications...")
        
        pending_notifications = Notification.objects.filter(
            status='pending',
            scheduled_for__lte=timezone.now()
        )
        
        sent_count = 0
        failed_count = 0
        
        for notification in pending_notifications:
            try:
                config = notification.user.alert_config
                
                # Send email if configured
                if config.notification_method in ['email', 'both']:
                    send_notification_email.delay(notification.id)
                    sent_count += 1
                
                # Mark as sent if not email-only
                if config.notification_method in ['dashboard', 'both']:
                    notification.mark_as_sent()
                    sent_count += 1
                
            except Exception as e:
                logger.error(f"Error sending notification {notification.id}: {str(e)}")
                notification.status = 'failed'
                notification.save()
                failed_count += 1
        
        logger.info(f"Notifications sent: {sent_count}, Failed: {failed_count}")
        return {
            'status': 'success',
            'sent': sent_count,
            'failed': failed_count
        }
    
    except Exception as e:
        logger.error(f"Error in send_pending_notifications: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True)
def send_notification_email(self, notification_id):
    """
    Send notification via email.
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
        subject = notification.title
        message = notification.message
        
        email_sent = send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        
        # Log the attempt
        NotificationLog.objects.create(
            user=user,
            notification=notification,
            message=message,
            delivery_method='email',
            success=bool(email_sent),
        )
        
        if email_sent:
            notification.mark_as_sent()
            logger.info(f"Email sent to {user.email} for notification {notification_id}")
            return {'status': 'success', 'email_sent': True}
        else:
            raise Exception("Email send returned False")
    
    except Exception as e:
        logger.error(f"Error sending email for notification {notification_id}: {str(e)}")
        try:
            NotificationLog.objects.create(
                user=notification.user,
                notification=notification,
                message=str(e),
                delivery_method='email',
                success=False,
                error_message=str(e),
            )
        except:
            pass
        raise self.retry(exc=e, countdown=300)


@shared_task
def cleanup_old_notifications():
    """
    Clean up old read notifications (older than 30 days).
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = Notification.objects.filter(
            status='read',
            read_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Deleted {deleted_count} old notifications")
        return {'status': 'success', 'deleted': deleted_count}
    
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        return {'status': 'error', 'message': str(e)}
