from django.core.management.base import BaseCommand

from ember_apps.leads.google_sheets import get_authorization_url


class Command(BaseCommand):
    help = 'Generate Google OAuth authorization URL for initial setup'

    def handle(self, *args, **options):
        auth_url = get_authorization_url()
        if not auth_url:
            self.stdout.write(
                self.style.ERROR(
                    'Google OAuth not configured. Please set GOOGLE_CLIENT_ID and '
                    'GOOGLE_CLIENT_SECRET in your .env file.'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('Google OAuth Authorization URL:'))
        self.stdout.write('')
        self.stdout.write(auth_url)
        self.stdout.write('')
        self.stdout.write(
            '1. Copy the URL above and open it in your browser\n'
            '2. Sign in with your Google account and grant permissions\n'
            '3. You will be redirected to the callback URL\n'
            '4. If successful, you will see "Authorization Successful"\n'
            '\n'
            'After authorization, urgent priority leads will be saved to Google Sheets.'
        )
