from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Direct one-on-one chat
    re_path(r'^ws/chat/(?P<recipient_id>\d+)/$', consumers.ChatConsumer.as_asgi()),

    # Group chat support
    re_path(r'^ws/group/(?P<group_id>\d+)/$', consumers.GroupChatConsumer.as_asgi()),
]
