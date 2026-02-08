"""
WSGI config for cosmic_watch project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cosmic_watch.settings')
application = get_wsgi_application()
