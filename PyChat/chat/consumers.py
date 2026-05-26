import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from .models import Conversation, Message, Presence


class PresenceMixin:
    @database_sync_to_async
    def update_presence(self, connected):
        presence, _ = Presence.objects.get_or_create(user=self.scope['user'])
        if connected:
            presence.active_connections += 1
            presence.is_online = True
        else:
            presence.active_connections = max(0, presence.active_connections - 1)
            presence.is_online = presence.active_connections > 0
            presence.last_seen = timezone.now()
        presence.last_seen = timezone.now()
        presence.save(update_fields=['active_connections', 'is_online', 'last_seen'])
        return presence

    @database_sync_to_async
    def get_online_participants(self, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        return list(conversation.participants.filter(presence__is_online=True).values_list('username', flat=True))


class ChatConsumer(PresenceMixin, AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        if not await self.user_in_conversation(self.conversation_id, self.scope['user']):
            await self.close()
            return

        await self.accept()
        await self.update_presence(True)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.broadcast_presence()
        await self.broadcast_read_receipts(await self.mark_messages_read())

    async def disconnect(self, close_code):
        await self.update_presence(False)
        await self.broadcast_presence()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get('action')

        if action == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.typing',
                    'user': self.scope['user'].username,
                    'is_typing': bool(content.get('is_typing', True)),
                },
            )
            return

        if action == 'read':
            message_ids = await self.mark_messages_read()
            await self.broadcast_read_receipts(message_ids)
            return

        if action == 'ping':
            await self.update_presence(True)
            await self.send_json({'type': 'pong', 'timestamp': timezone.now().isoformat()})
            return

        message_text = content.get('message', '').strip()
        if not message_text:
            return

        message = await self.create_message(
            conversation_id=self.conversation_id,
            sender=self.scope['user'],
            content=message_text,
        )

        payload = {
            'type': 'chat.message',
            'message_id': message.id,
            'conversation_id': self.conversation_id,
            'sender': self.scope['user'].username,
            'content': message.content,
            'attachment_url': None,
            'attachment_name': None,
            'created_at': message.created_at.isoformat(),
            'deleted': message.deleted,
            'edited': message.edited,
            'read_by_count': message.read_by.count(),
        }

        await self.channel_layer.group_send(self.room_group_name, payload)

    async def chat_message(self, event):
        await self.send_json({
            'type': 'message',
            'message_id': event['message_id'],
            'conversation_id': event['conversation_id'],
            'sender': event['sender'],
            'content': event['content'],
            'attachment_url': event.get('attachment_url'),
            'attachment_name': event.get('attachment_name'),
            'created_at': event['created_at'],
            'deleted': event.get('deleted', False),
            'edited': event.get('edited', False),
            'read_by_count': event.get('read_by_count', 0),
        })

    async def chat_typing(self, event):
        await self.send_json({
            'type': 'typing',
            'user': event['user'],
            'is_typing': event['is_typing'],
        })

    async def chat_presence(self, event):
        await self.send_json({
            'type': 'presence',
            'online': event['online'],
        })

    async def chat_read_receipt(self, event):
        await self.send_json({
            'type': 'read_receipt',
            'reader': event['reader'],
            'message_ids': event['message_ids'],
        })

    async def chat_edit_message(self, event):
        await self.send_json({
            'type': 'message_edit',
            'message_id': event['message_id'],
            'sender': event.get('sender'),
            'content': event['content'],
            'created_at': event.get('created_at'),
            'edited': event['edited'],
            'deleted': False,
            'read_by_count': 0,
        })

    async def chat_delete_message(self, event):
        await self.send_json({
            'type': 'message_delete',
            'message_id': event['message_id'],
            'sender': event.get('sender'),
            'created_at': event.get('created_at'),
        })

    async def broadcast_presence(self):
        online = await self.get_online_participants(self.conversation_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.presence',
                'online': online,
            },
        )

    async def broadcast_read_receipts(self, message_ids):
        if not message_ids:
            return
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.read_receipt',
                'reader': self.scope['user'].username,
                'message_ids': message_ids,
            },
        )

    @database_sync_to_async
    def mark_messages_read(self):
        conversation = Conversation.objects.get(id=self.conversation_id)
        unread_messages = conversation.messages.exclude(sender=self.scope['user']).exclude(read_by=self.scope['user'])
        message_ids = []
        for message in unread_messages:
            message.read_by.add(self.scope['user'])
            message_ids.append(message.id)
        return message_ids

    @database_sync_to_async
    def user_in_conversation(self, conversation_id, user):
        return Conversation.objects.filter(id=conversation_id, participants=user).exists()

    @database_sync_to_async
    def create_message(self, conversation_id, sender, content):
        conversation = Conversation.objects.get(id=conversation_id)
        return Message.objects.create(conversation=conversation, sender=sender, content=content)


class NotificationsConsumer(PresenceMixin, AsyncJsonWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.user_group_name = f'notifications_{self.scope['user'].id}'
        await self.accept()
        await self.update_presence(True)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.send_json({'type': 'notifications.connected'})

    async def disconnect(self, close_code):
        await self.update_presence(False)
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('action') == 'ping':
            await self.update_presence(True)
            await self.send_json({'type': 'pong', 'timestamp': timezone.now().isoformat()})
            return

        if content.get('type') == 'notification.message':
            await self.channel_layer.group_send(
                self.user_group_name,
                {
                    'type': 'notification.message',
                    'conversation_id': content.get('conversation_id'),
                    'conversation_name': content.get('conversation_name', ''),
                    'sender': content.get('sender', ''),
                    'last_message': content.get('last_message', ''),
                    'created_at': content.get('created_at'),
                    'unread_count': content.get('unread_count', 0),
                }
            )
            return

    async def notification_message(self, event):
        await self.send_json(event)
