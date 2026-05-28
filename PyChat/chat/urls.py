from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/<str:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/create/', views.create_conversation, name='create_conversation'),
    path('friends/<int:user_id>/chat/', views.direct_chat, name='direct_chat'),
    path('conversations/<str:conversation_id>/history/', views.message_history, name='message_history'),
    path('conversations/<str:conversation_id>/action/', views.conversation_action, name='conversation_action'),
    path('conversations/<str:conversation_id>/send/', views.send_message, name='send_message'),
    path('conversations/<str:conversation_id>/upload/', views.upload_attachment, name='upload_attachment'),
    path('conversations/message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('conversations/message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('friends/', views.friends_view, name='friends'),
    path('friends/find/', views.find_friends_view, name='find_friends'),
]