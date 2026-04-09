from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from .google_sheets import exchange_code_for_tokens, get_authorization_url
from .oauth_models import GoogleOAuthToken


class GoogleAuthorizeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        auth_url = get_authorization_url()
        if not auth_url:
            return JsonResponse(
                {'error': 'Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return JsonResponse({'authorization_url': auth_url})


class GoogleCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return JsonResponse(
                {'error': 'Missing authorization code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_data = exchange_code_for_tokens(code)
        if not token_data:
            return JsonResponse(
                {'error': 'Failed to exchange code for tokens'},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)

        if not access_token or not refresh_token:
            return JsonResponse(
                {'error': 'Missing access_token or refresh_token in response'},
                status=status.HTTP_400_BAD_REQUEST
            )

        import os
        token_obj, _ = GoogleOAuthToken.objects.update_or_create(
            id=1,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
                'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
                'expires_at': timezone.now() + timedelta(seconds=expires_in - 60),
            }
        )

        return HttpResponse(
            '<h1>Authorization Successful</h1>'
            '<p>You can close this window and return to the application.</p>'
            '<script>setTimeout(() => window.close(), 3000);</script>'
        )


class GoogleAuthStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        is_configured = bool(
            GoogleOAuthToken.objects.filter(id=1).exists()
        )
        return JsonResponse({'is_authorized': is_configured})


class GoogleDisconnectView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request):
        GoogleOAuthToken.objects.filter(id=1).delete()
        return JsonResponse({'disconnected': True})
