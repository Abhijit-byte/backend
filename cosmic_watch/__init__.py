"""
CosmosTrace Django Project
Real-time NEO (Near-Earth Object) Monitoring System
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
