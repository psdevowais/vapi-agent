from django.urls import path

from . import views
from .oauth_views import GoogleAuthorizeView, GoogleAuthStatusView, GoogleCallbackView, GoogleDisconnectView
from .sync_views import SyncSheetsToDBView

urlpatterns = [
    path('auth/google', GoogleAuthorizeView.as_view(), name='google-authorize'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('auth/google/status', GoogleAuthStatusView.as_view(), name='google-auth-status'),
    path('auth/google/disconnect', GoogleDisconnectView.as_view(), name='google-disconnect'),
    path('sheets/sync', SyncSheetsToDBView.as_view(), name='sheets-sync'),
    path('vapi/verify-owner', views.VerifyOwnerView.as_view(), name='verify-owner'),
    path('vapi/update-info', views.UpdateInfoView.as_view(), name='update-info'),
]
