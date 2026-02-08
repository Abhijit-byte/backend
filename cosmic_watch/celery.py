"""
Celery configuration for CosmosTrace project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cosmic_watch.settings')

app = Celery('cosmic_watch')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'fetch-asteroids-every-hour': {
        'task': 'tracker.tasks.fetch_asteroids_data',
        'schedule': crontab(minute=0),  # Every hour
    },
    'check-close-approaches-every-30-mins': {
        'task': 'tracker.tasks.check_and_notify_close_approaches',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'send-pending-notifications-every-5-mins': {
        'task': 'tracker.tasks.send_pending_notifications',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
