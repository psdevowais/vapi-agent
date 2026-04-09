import os

from django.core.management.base import BaseCommand

from ember_apps.leads.google_sheets import get_or_refresh_credentials
from ember_apps.leads.models import Property


class Command(BaseCommand):
    help = 'Sync leads from Google Sheets to PostgreSQL Property table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
        if not spreadsheet_id:
            self.stderr.write(self.style.ERROR('GOOGLE_SHEETS_SPREADSHEET_ID not set'))
            return

        creds = get_or_refresh_credentials()
        if not creds:
            self.stderr.write(self.style.ERROR('Failed to get Google credentials'))
            return

        from googleapiclient.discovery import build
        service = build('sheets', 'v4', credentials=creds)
        sheets = service.spreadsheets()

        worksheet_name = os.environ.get('GOOGLE_SHEETS_PROPERTY_WORKSHEET', 'Property DB').strip() or 'Property DB'

        result = sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=worksheet_name,
        ).execute()

        values = result.get('values', [])
        if not values:
            self.stdout.write(self.style.WARNING('No data found in Google Sheet'))
            return

        headers = [h.strip().lower() for h in values[0]]
        rows = values[1:]

        self.stdout.write(f'Found {len(rows)} rows in Google Sheet')
        self.stdout.write(f'Headers: {headers}')

        created = 0
        updated = 0
        skipped = 0

        for row_idx, row in enumerate(rows, start=2):
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header] = row[i].strip()

            self.stdout.write(f'--- Row {row_idx} ---')
            self.stdout.write(f'  Raw row_dict: {row_dict}')

            caller_name = row_dict.get('caller_name', '')
            caller_phone = row_dict.get('caller_phone', '')
            caller_email = row_dict.get('caller_email', '')
            property_address = row_dict.get('property_address', '')

            self.stdout.write(f'  Extracted: name="{caller_name}", phone="{caller_phone}", email="{caller_email}", address="{property_address}"')

            if not caller_name and not caller_phone and not caller_email and not property_address:
                skipped += 1
                continue

            defaults = {
                'caller_name': caller_name,
                'caller_phone': caller_phone,
                'caller_email': caller_email,
                'property_address': property_address,
                'property_status': row_dict.get('property_status', ''),
                'sell_timeframe': row_dict.get('sell_timeframe', ''),
                'price_listing': row_dict.get('price_listing', ''),
                'occupancy_status': row_dict.get('occupancy_status', ''),
                'call_priority': row_dict.get('call_priority', ''),
                'call_reason': row_dict.get('call_reason', ''),
                'additional_notes': row_dict.get('additional_notes', ''),
            }

            self.stdout.write(f'  Defaults: {defaults}')

            lookup = {}
            if caller_phone:
                lookup['caller_phone'] = caller_phone
            elif caller_email:
                lookup['caller_email'] = caller_email
            elif property_address:
                lookup['property_address'] = property_address
            else:
                lookup['caller_name'] = caller_name

            self.stdout.write(f'  Lookup: {lookup}')

            if dry_run:
                existing = Property.objects.filter(**lookup).first()
                if existing:
                    self.stdout.write(f'  Would UPDATE - {caller_name} ({property_address})')
                    updated += 1
                else:
                    self.stdout.write(f'  Would CREATE - {caller_name} ({property_address})')
                    created += 1
            else:
                obj, is_created = Property.objects.update_or_create(
                    **lookup,
                    defaults=defaults,
                )
                if is_created:
                    self.stdout.write(f'  CREATED - {obj.caller_name} ({obj.property_address}) | status="{obj.property_status}", occupancy="{obj.occupancy_status}"')
                    created += 1
                else:
                    self.stdout.write(f'  UPDATED - {obj.caller_name} ({obj.property_address}) | status="{obj.property_status}", occupancy="{obj.occupancy_status}"')
                    updated += 1

        action = 'DRY RUN - ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'{action}Sync complete: {created} created, {updated} updated, {skipped} skipped'
        ))
