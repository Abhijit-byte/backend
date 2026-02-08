"""
Django Channels consumers for real-time notifications.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = f'notifications_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {self.user.username} connected to notifications")
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to notification service',
            'unread_count': unread_count
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"User {self.user.username} disconnected from notifications")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_as_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_as_read(notification_id)
            
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")

    async def notification_event(self, event):
        """Handle notification events."""
        notification = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': notification.get('id'),
            'title': notification.get('title'),
            'message': notification.get('message'),
            'asteroid': notification.get('asteroid_name'),
            'approach_date': notification.get('approach_date'),
            'timestamp': timezone.now().isoformat()
        }))

    async def unread_count_update(self, event):
        """Handle unread count updates."""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'unread_count': event['unread_count']
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user."""
        from .models import Notification
        return Notification.objects.filter(
            user=self.user,
            status__in=['pending', 'sent']
        ).count()

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Mark notification as read."""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {self.user.username}")
