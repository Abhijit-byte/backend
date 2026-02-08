"""
ASGI config for cosmic_watch project with WebSocket support.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cosmic_watch.settings')

django_asgi_app = get_asgi_application()

from tracker.consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/notifications/', AuthMiddlewareStack(URLRouter([
        path('', NotificationConsumer.as_asgi()),
    ]))),
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
