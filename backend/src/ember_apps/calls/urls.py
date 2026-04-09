from django.urls import path

from . import views, twilio_views

urlpatterns = [
    # Existing endpoints
    path('calls', views.CallListCreateView.as_view(), name='call-list-create'),
    path('calls/<uuid:pk>', views.CallDetailView.as_view(), name='call-detail'),
    path('analytics', views.AnalyticsView.as_view(), name='analytics'),
    path('vapi/webhook', views.VapiWebhookView.as_view(), name='vapi-webhook'),
    path('calls/vapi/lookup-info', views.LookupInfoView.as_view(), name='lookup-info'),
    
    # Twilio outbound calling endpoints
    path('twilio/outbound', twilio_views.initiate_outbound_call, name='twilio-outbound'),
    path('twilio/calls/<str:call_id>/status', twilio_views.get_call_status, name='twilio-call-status'),
    path('twilio/calls/<str:call_id>/end', twilio_views.end_call, name='twilio-end-call'),
    
    # Twilio webhooks (no auth required)
    path('twilio/voice-stream/<str:call_id>/', twilio_views.twilio_voice_stream, name='twilio-voice-stream'),
    path('twilio/status/', twilio_views.twilio_status_callback, name='twilio-status-callback'),

    # Test endpoint for webhook debugging
    path('twilio/test-voice/', twilio_views.test_voice_webhook, name='twilio-test-voice'),
]
