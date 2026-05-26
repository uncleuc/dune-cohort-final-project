import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    active_users = {}

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        if not await self.user_in_conversation(self.conversation_id, self.scope['user']):
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.add_presence_user()
        await self.accept()
        await self.broadcast_presence()
        await self.broadcast_read_receipts(await self.mark_messages_read())

    async def disconnect(self, close_code):
        self.remove_presence_user()
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

    def add_presence_user(self):
        users = self.active_users.setdefault(self.conversation_id, set())
        users.add(self.scope['user'].username)

    def remove_presence_user(self):
        users = self.active_users.get(self.conversation_id)
        if not users:
            return
        users.discard(self.scope['user'].username)
        if not users:
            del self.active_users[self.conversation_id]

    async def broadcast_presence(self):
        online = list(self.active_users.get(self.conversation_id, []))
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
