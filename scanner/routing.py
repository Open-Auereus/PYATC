from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/scanner/$', consumers.ScannerConsumer.as_asgi()),
]
