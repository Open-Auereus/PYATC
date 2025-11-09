from django.urls import path
from . import views

app_name = 'scanner'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.settings_page, name='settings'),
    path('history/', views.history, name='history'),

    path('api/start/', views.start_scanner, name='start_scanner'),
    path('api/stop/', views.stop_scanner, name='stop_scanner'),
    path('api/status/', views.get_status, name='get_status'),
    path('api/settings/', views.update_settings, name='update_settings'),
    path('api/next-audio/', views.get_next_audio, name='get_next_audio'),
    path('api/transmissions/', views.transmissions_list, name='transmissions_list'),
]
