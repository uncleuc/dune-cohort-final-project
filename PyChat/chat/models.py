from django.conf import settings
from django.db import models


class Conversation(models.Model):
    name = models.CharField(max_length=255, blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
    )
    archived_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='archived_conversations',
        blank=True,
    )
    blocked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='blocked_conversations',
        blank=True,
    )
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f'Conversation {self.pk}'


class FriendRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='friend_requests_sent',
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='friend_requests_received',
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.from_user} -> {self.to_user} ({self.status})'


class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='blocks_initiated',
        on_delete=models.CASCADE,
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='blocks_received',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.blocker} blocked {self.blocked}'


class Presence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='presence',
        on_delete=models.CASCADE,
    )
    is_online = models.BooleanField(default=False)
    active_connections = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} online={self.is_online} last_seen={self.last_seen}'


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        related_name='messages',
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='messages',
        on_delete=models.CASCADE,
    )
    content = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to='chat_attachments/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_messages',
        blank=True,
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} @ {self.created_at:%Y-%m-%d %H:%M}: {self.content[:40]}'
