import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import Block, Conversation, Message, FriendRequest, Presence


def home(request):
    if request.user.is_authenticated:
        return redirect('conversation_list')
    return render(request, 'chat/home.html')


def get_friend_ids(user):
    accepted_requests = FriendRequest.objects.filter(
        status=FriendRequest.STATUS_ACCEPTED
    ).filter(
        Q(from_user=user) | Q(to_user=user)
    ).values_list('from_user_id', 'to_user_id')

    friend_ids = set()
    for from_user_id, to_user_id in accepted_requests:
        friend_ids.add(to_user_id if from_user_id == user.id else from_user_id)
    return friend_ids


def get_blocked_user_ids(user):
    blocked_ids = set(Block.objects.filter(blocker=user).values_list('blocked_id', flat=True))
    blocked_ids.update(Block.objects.filter(blocked=user).values_list('blocker_id', flat=True))
    return blocked_ids


def get_friends(user):
    friend_ids = get_friend_ids(user)
    blocked_ids = get_blocked_user_ids(user)
    return User.objects.filter(id__in=friend_ids).exclude(id__in=blocked_ids)


def get_avatar_url(user):
    profile = getattr(user, 'account_profile', None)
    return profile.profile_picture.url if profile and profile.profile_picture else None


def get_other_user(conversation, user):
    return conversation.participants.exclude(id=user.id).first()


@login_required
@require_http_methods(["GET", "POST"])
def find_friends_view(request):
    search_query = request.GET.get('q', '').strip()
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_request':
            target_user_id = request.POST.get('target_user_id')
            target_user = get_object_or_404(User, pk=target_user_id)

            if target_user != request.user and not FriendRequest.objects.filter(
                from_user=request.user,
                to_user=target_user,
            ).exists() and not FriendRequest.objects.filter(
                from_user=target_user,
                to_user=request.user,
            ).exists():
                FriendRequest.objects.create(
                    from_user=request.user,
                    to_user=target_user,
                )

        elif action == 'accept_request':
            request_id = request.POST.get('friend_request_id')
            friend_request = get_object_or_404(
                FriendRequest,
                pk=request_id,
                to_user=request.user,
                status=FriendRequest.STATUS_PENDING,
            )
            friend_request.status = FriendRequest.STATUS_ACCEPTED
            friend_request.save()

        return redirect('find_friends')

    incoming_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status=FriendRequest.STATUS_PENDING,
    ).order_by('-created_at')

    outgoing_pending_ids = set(FriendRequest.objects.filter(
        from_user=request.user,
        status=FriendRequest.STATUS_PENDING,
    ).values_list('to_user_id', flat=True))

    friend_ids = get_friend_ids(request.user)
    incoming_from_ids = set(incoming_requests.values_list('from_user_id', flat=True))
    excluded_ids = {request.user.id} | friend_ids | outgoing_pending_ids | incoming_from_ids

    blocked_ids = get_blocked_user_ids(request.user)
    excluded_ids |= blocked_ids

    users = User.objects.exclude(id__in=excluded_ids)
    if search_query:
        users = users.filter(username__icontains=search_query)

    for user_item in users:
        user_item.avatar_url = get_avatar_url(user_item)

    return render(request, 'chat/find_friends.html', {
        'incoming_requests': incoming_requests,
        'users': users,
        'query': search_query,
        'outgoing_pending_ids': outgoing_pending_ids,
        'friends': get_friends(request.user),
    })


def get_direct_conversation(user, friend):
    return Conversation.objects.annotate(
        participant_count=Count('participants')
    ).filter(
        is_group=False,
        participant_count=2,
    ).filter(
        participants=user,
    ).filter(
        participants=friend,
    ).first()


def get_conversation_display_name(user, conversation):
    if conversation.name:
        return conversation.name
    if conversation.is_group:
        return f'Group Chat'
    other = conversation.participants.exclude(id=user.id).first()
    return other.username if other else f'Conversation {conversation.id}'


def get_unread_count(conversation, user):
    return conversation.messages.exclude(sender=user).exclude(read_by=user).count()


def is_friend_conversation(user, conversation):
    friend_ids = get_friend_ids(user)
    other_ids = set(conversation.participants.exclude(id=user.id).values_list('id', flat=True))
    if not other_ids:
        return False
    if other_ids & get_blocked_user_ids(user):
        return False
    return other_ids.issubset(friend_ids)


def broadcast_conversation_notification(conversation, sender_username, last_message, created_at):
    channel_layer = get_channel_layer()
    for participant in conversation.participants.exclude(username=sender_username):
        unread_count = get_unread_count(conversation, participant)
        async_to_sync(channel_layer.group_send)(
            f'notifications_{participant.id}',
            {
                'type': 'notification.message',
                'conversation_id': conversation.id,
                'conversation_name': conversation.name or '',
                'sender': sender_username,
                'last_message': last_message,
                'created_at': created_at,
                'unread_count': unread_count,
            }
        )


@login_required
def direct_chat(request, user_id):
    friend = get_object_or_404(User, pk=user_id)
    if friend.id == request.user.id:
        return redirect('friends')

    if friend.id not in get_friend_ids(request.user):
        return redirect('friends')

    if friend.id in get_blocked_user_ids(request.user):
        return redirect('friends')

    conversation = get_direct_conversation(request.user, friend)
    if not conversation:
        conversation = Conversation.objects.create(name='', is_group=False)
        conversation.participants.add(request.user, friend)

    return redirect('conversation_detail', conversation_id=conversation.id)


@login_required
def conversation_list(request):
    conversations = []
    blocked_ids = get_blocked_user_ids(request.user)
    for conversation in Conversation.objects.filter(participants=request.user):
        if conversation.archived_by.filter(id=request.user.id).exists() or conversation.blocked_by.filter(id=request.user.id).exists():
            continue

        if conversation.is_group or is_friend_conversation(request.user, conversation):
            messages = conversation.messages.all().order_by('-created_at')
            conversation.last_message = messages.first()
            conversation.display_name = get_conversation_display_name(request.user, conversation)
            conversation.other_user = get_other_user(conversation, request.user)
            conversation.avatar_url = get_avatar_url(conversation.other_user) if conversation.other_user else None
            conversation.unread_count = get_unread_count(conversation, request.user)
            conversation.sort_key = conversation.last_message.created_at if conversation.last_message else conversation.created_at
            conversations.append(conversation)

    conversations.sort(key=lambda conv: conv.sort_key, reverse=True)
    return render(request, 'chat/conversation_list.html', {'conversations': conversations})


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    if conversation.archived_by.filter(id=request.user.id).exists() or conversation.blocked_by.filter(id=request.user.id).exists():
        return redirect('conversation_list')

    if not (is_friend_conversation(request.user, conversation) or conversation.is_group):
        return redirect('conversation_list')

    chat_messages = conversation.messages.all()
    conversations = []
    for conv in Conversation.objects.filter(participants=request.user):
        if conv.archived_by.filter(id=request.user.id).exists() or conv.blocked_by.filter(id=request.user.id).exists():
            continue
        if is_friend_conversation(request.user, conv) or conv.is_group:
            conv.display_name = get_conversation_display_name(request.user, conv)
            conversations.append(conv)

    conversation.display_name = get_conversation_display_name(request.user, conversation)
    other_presence = None
    if not conversation.is_group:
        other_user = get_other_user(conversation, request.user)
        if other_user:
            other_presence = Presence.objects.filter(user=other_user).first()
            conversation.other_user = other_user
            conversation.avatar_url = get_avatar_url(other_user)

    return render(request, 'chat/conversation_detail.html', {
        'conversation': conversation,
        'chat_messages': chat_messages,
        'conversations': conversations,
        'selected_conversation_id': conversation.id,
        'other_presence': other_presence,
    })


@login_required
@require_POST
def conversation_action(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    action = request.POST.get('action')

    if action == 'archive':
        conversation.archived_by.add(request.user)
        return JsonResponse({'success': True, 'message': 'Conversation archived.'})

    if action == 'clear':
        conversation.messages.all().delete()
        return JsonResponse({'success': True, 'message': 'Chat cleared.'})

    if action == 'delete':
        conversation.delete()
        return JsonResponse({'success': True, 'message': 'Conversation deleted.'})

    if action == 'block':
        if not conversation.is_group:
            other = conversation.participants.exclude(id=request.user.id).first()
            if other:
                Block.objects.get_or_create(blocker=request.user, blocked=other)
        conversation.archived_by.add(request.user)
        conversation.blocked_by.add(request.user)
        return JsonResponse({'success': True, 'message': 'Conversation blocked and hidden.'})

    return JsonResponse({'success': False, 'message': 'Unknown action.'}, status=400)


@login_required
def friends_view(request):
    friends = get_friends(request.user)
    for friend in friends:
        friend.avatar_url = get_avatar_url(friend)
    return render(request, 'chat/friends.html', {
        'friends': friends,
    })


@login_required
@require_POST
def send_message(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Message content required'}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
    )

    channel_layer = get_channel_layer()
    room_group_name = f'chat_{conversation_id}'
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'chat.message',
            'message_id': message.id,
            'conversation_id': conversation_id,
            'sender': request.user.username,
            'content': message.content,
            'attachment_url': None,
            'attachment_name': None,
            'created_at': message.created_at.isoformat(),
            'deleted': message.deleted,
            'edited': message.edited,
            'read_by_count': message.read_by.count(),
        }
    )
    broadcast_conversation_notification(
        conversation,
        request.user.username,
        message.content or 'New message',
        message.created_at.isoformat(),
    )

    return JsonResponse({
        'message_id': message.id,
        'conversation_id': conversation_id,
        'sender': request.user.username,
        'content': message.content,
        'attachment_url': None,
        'attachment_name': None,
        'created_at': message.created_at.isoformat(),
        'deleted': message.deleted,
        'edited': message.edited,
        'read_by_count': message.read_by.count(),
    })


@login_required
@require_POST
def upload_attachment(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    attachment = request.FILES.get('attachment')
    content = request.POST.get('content', '').strip()

    if not attachment:
        return JsonResponse({'error': 'No attachment provided.'}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
        attachment=attachment,
    )

    attachment_name = os.path.basename(message.attachment.name)
    channel_layer = get_channel_layer()
    room_group_name = f'chat_{conversation_id}'
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'chat.message',
            'message_id': message.id,
            'conversation_id': conversation_id,
            'sender': request.user.username,
            'content': message.content,
            'attachment_url': message.attachment.url,
            'attachment_name': attachment_name,
            'created_at': message.created_at.isoformat(),
            'deleted': message.deleted,
            'edited': message.edited,
            'read_by_count': message.read_by.count(),
        }
    )
    broadcast_conversation_notification(
        conversation,
        request.user.username,
        message.content or 'Attachment',
        message.created_at.isoformat(),
    )

    return JsonResponse({
        'message_id': message.id,
        'conversation_id': conversation_id,
        'sender': request.user.username,
        'content': message.content,
        'attachment_url': message.attachment.url,
        'attachment_name': attachment_name,
        'created_at': message.created_at.isoformat(),
        'deleted': message.deleted,
        'edited': message.edited,
        'read_by_count': message.read_by.count(),
    })


@login_required
@require_POST
def edit_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    conversation = message.conversation
    if request.user not in conversation.participants.all():
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Message content required.'}, status=400)

    if message.deleted:
        return JsonResponse({'error': 'Cannot edit a deleted message.'}, status=400)

    message.content = content
    message.edited = True
    message.save()

    channel_layer = get_channel_layer()
    room_group_name = f'chat_{conversation.id}'
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'chat.edit_message',
            'message_id': message.id,
            'sender': request.user.username,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'edited': message.edited,
        }
    )

    return JsonResponse({'success': True, 'message': 'Message edited.'})


@login_required
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    conversation = message.conversation
    if request.user not in conversation.participants.all():
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    message.deleted = True
    message.save()

    channel_layer = get_channel_layer()
    room_group_name = f'chat_{conversation.id}'
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'chat.delete_message',
            'message_id': message.id,
            'sender': request.user.username,
            'created_at': message.created_at.isoformat(),
        }
    )

    return JsonResponse({'success': True, 'message': 'Message deleted.'})


@login_required
def create_conversation(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        participants_ids = request.POST.getlist('participants')

        if len(participants_ids) < 2:
            return JsonResponse({'error': 'Choose at least two friends to create a group chat.'}, status=400)

        friends = get_friends(request.user)
        participants = friends.filter(id__in=participants_ids)
        if participants.count() != len(participants_ids):
            return JsonResponse({'error': 'Invalid participants'}, status=400)

        conversation = Conversation.objects.create(name=name or 'New Group Chat', is_group=True)
        conversation.participants.add(request.user)
        conversation.participants.add(*participants)

        return redirect('conversation_detail', conversation_id=conversation.id)

    users = get_friends(request.user)
    return render(request, 'chat/create_conversation.html', {'users': users})


@login_required
def message_history(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    messages = conversation.messages.all().order_by('created_at')
    message_ids = []
    for msg in messages.exclude(sender=request.user).exclude(read_by=request.user):
        msg.read_by.add(request.user)
        message_ids.append(msg.id)

    data = [{
        'id': msg.id,
        'sender': msg.sender.username,
        'content': msg.content,
        'attachment_url': msg.attachment.url if msg.attachment else None,
        'attachment_name': os.path.basename(msg.attachment.name) if msg.attachment else None,
        'created_at': msg.created_at.isoformat(),
        'edited': msg.edited,
        'deleted': msg.deleted,
        'read_by_count': msg.read_by.count(),
        'read_by': list(msg.read_by.values_list('username', flat=True)),
    } for msg in messages]

    if message_ids:
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation_id}'
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat.read_receipt',
                'reader': request.user.username,
                'message_ids': message_ids,
            }
        )

    return JsonResponse({'messages': data})

