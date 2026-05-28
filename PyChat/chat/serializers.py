from rest_framework import serializers

from .models import Conversation, Message


class ChatSerializer(serializers.ModelSerializer):
    participant_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'name',
            'participants',
            'archived_by',
            'blocked_by',
            'is_group',
            'is_favorite',
            'created_at',
            'participant_count',
            'last_message',
        ]

    def get_last_message(self, obj):
        message = obj.messages.order_by('-created_at').first()
        if not message:
            return None
        return {
            'id': message.id,
            'sender': message.sender.username,
            'content': message.content,
            'created_at': message.created_at,
            'attachment': message.attachment.url if message.attachment else None,
        }


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
