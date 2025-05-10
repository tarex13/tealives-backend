import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, GroupChat  # Ensure you have GroupChat model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.recipient_id = self.scope['url_route']['kwargs']['recipient_id']
        self.sender = self.scope["user"]

        if not self.sender.is_authenticated:
            await self.close()
            return

        self.room_group_name = f'chat_{min(self.sender.id, self.recipient_id)}_{max(self.sender.id, self.recipient_id)}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()
        is_typing = data.get('typing', False)

        if is_typing:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_event',
                    'sender_id': self.sender.id,
                }
            )
            return

        if message_content:
            await self.save_message(self.sender.id, self.recipient_id, message_content)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'sender_id': self.sender.id,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
        }))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            'typing': True,
            'sender_id': event['sender_id'],
        }))

    @database_sync_to_async
    def save_message(self, sender_id, recipient_id, content):
        sender = User.objects.get(id=sender_id)
        recipient = User.objects.get(id=recipient_id)
        Message.objects.create(sender=sender, recipient=recipient, content=content)


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'group_{self.group_id}'
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()
        is_typing = data.get('typing', False)

        if is_typing:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_event',
                    'sender_id': self.user.id,
                }
            )
            return

        if message_content:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'group_message',
                    'message': message_content,
                    'sender_id': self.user.id,
                }
            )

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
        }))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            'typing': True,
            'sender_id': event['sender_id'],
        }))
        
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()
        is_typing = data.get('typing', False)

        if is_typing:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_event',
                    'sender_id': self.user.id,
                }
            )
            return

        if message_content:
            # Save and broadcast message
            await self.save_message(message_content)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'group_message',
                    'message': message_content,
                    'sender_id': self.user.id,
                }
            )

        async def typing_event(self, event):
            await self.send(text_data=json.dumps({
                'typing': True,
                'sender_id': event['sender_id'],
            }))

    @database_sync_to_async
    def save_message(self, content):
        GroupMessage.objects.create(
            group_id=self.group_id, sender=self.user, content=content
        )

