from django.db import models


class GoogleOAuthToken(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_uri = models.URLField(default='https://oauth2.googleapis.com/token')
    client_id = models.CharField(max_length=256)
    client_secret = models.CharField(max_length=256)
    scopes = models.TextField(default='https://www.googleapis.com/auth/spreadsheets')
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Google OAuth Token'
        verbose_name_plural = 'Google OAuth Tokens'

    def __str__(self):
        return f'Google OAuth Token (updated: {self.updated_at})'
