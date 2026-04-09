from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/transcript/(?P<call_id>[0-9a-f-]+)/$", consumers.TranscriptConsumer.as_asgi()),
    re_path(r"^ws/voice/$", consumers.VoiceConsumer.as_asgi()),
]
