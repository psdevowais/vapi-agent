import os
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .oauth_models import GoogleOAuthToken


SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.send',
]


def get_client_config():
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
    if not client_id or not client_secret:
        return None
    return {
        'client_id': client_id,
        'client_secret': client_secret,
    }


def get_authorization_url():
    config = get_client_config()
    if not config:
        return None

    redirect_uri = os.environ.get(
        'GOOGLE_REDIRECT_URI',
        'http://127.0.0.1:8000/api/auth/google/callback/'
    )

    params = {
        'client_id': config['client_id'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict | None:
    config = get_client_config()
    if not config:
        return None

    redirect_uri = os.environ.get(
        'GOOGLE_REDIRECT_URI',
        'http://127.0.0.1:8000/api/auth/google/callback/'
    )

    response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'code': code,
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        },
        timeout=30,
    )

    if response.status_code != 200:
        return None

    return response.json()


def get_or_refresh_credentials() -> Credentials | None:
    try:
        token_obj = GoogleOAuthToken.objects.get(id=1)
    except GoogleOAuthToken.DoesNotExist:
        return None

    config = get_client_config()
    if not config:
        return None

    if token_obj.expires_at and timezone.now() >= token_obj.expires_at:
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'refresh_token': token_obj.refresh_token,
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'grant_type': 'refresh_token',
            },
            timeout=30,
        )

        if response.status_code != 200:
            return None

        token_data = response.json()
        token_obj.access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        token_obj.expires_at = timezone.now() + timedelta(seconds=expires_in - 60)
        token_obj.save(update_fields=['access_token', 'expires_at', 'updated_at'])

    return Credentials(
        token=token_obj.access_token,
        refresh_token=token_obj.refresh_token,
        token_uri=token_obj.token_uri,
        client_id=token_obj.client_id,
        client_secret=token_obj.client_secret,
        scopes=SCOPES,
    )


def get_sheet_values(spreadsheet_id: str, range_name: str) -> list[list[str]] | None:
    creds = get_or_refresh_credentials()
    if not creds:
        return None

    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    result = sheets.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
    ).execute()

    return result.get('values', [])


def append_lead_row(values: list[str]) -> None:
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
    if not spreadsheet_id:
        return

    creds = get_or_refresh_credentials()
    if not creds:
        return

    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    worksheet_name = os.environ.get('GOOGLE_SHEETS_WORKSHEET_NAME', 'Leads').strip() or 'Leads'

    sheets.values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{worksheet_name}!A1",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': [values]},
    ).execute()


def append_normal_lead_row(lead_data: dict) -> None:
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
    if not spreadsheet_id:
        return

    creds = get_or_refresh_credentials()
    if not creds:
        return

    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    worksheet_name = os.environ.get('GOOGLE_SHEETS_NORMAL_WORKSHEET_NAME', 'Normal Leads').strip() or 'Normal Leads'

    values = [
        lead_data.get('caller_name', ''),
        lead_data.get('caller_phone', ''),
        lead_data.get('caller_email', ''),
        lead_data.get('property_address', ''),
        lead_data.get('sell_timeframe', ''),
        lead_data.get('occupancy_status', ''),
        lead_data.get('call_reason', ''),
        lead_data.get('call_priority', ''),
        lead_data.get('additional_notes', ''),
        lead_data.get('created_at', ''),
    ]

    sheets.values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{worksheet_name}!A1",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': [values]},
    ).execute()


def update_property_db_row(property_data: dict) -> bool:
    """Update existing property row in Property DB sheet or append if not found."""
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
    if not spreadsheet_id:
        return False

    creds = get_or_refresh_credentials()
    if not creds:
        return False

    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    worksheet_name = os.environ.get('GOOGLE_SHEETS_PROPERTY_WORKSHEET', 'Property DB').strip() or 'Property DB'
    range_name = f"{worksheet_name}!A1:L1000"

    # Get existing data
    try:
        result = sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()
        rows = result.get('values', [])
    except Exception:
        rows = []

    # Prepare row values in correct order
    values = [
        property_data.get('caller_name', ''),
        property_data.get('caller_phone', ''),
        property_data.get('caller_email', ''),
        property_data.get('property_address', ''),
        property_data.get('property_status', ''),
        property_data.get('sell_timeframe', ''),
        property_data.get('price_listing', ''),
        property_data.get('occupancy_status', ''),
        property_data.get('call_priority', ''),
        property_data.get('call_reason', ''),
        property_data.get('additional_notes', ''),
        property_data.get('updated_at', property_data.get('created_at', '')),
    ]

    # Search for matching row by phone, email, or address
    row_index = None
    for i, row in enumerate(rows[1:] if rows else [], start=2):  # Skip header row
        if len(row) >= 4:
            sheet_phone = row[1] if len(row) > 1 else ''
            sheet_email = row[2] if len(row) > 2 else ''
            sheet_address = row[3] if len(row) > 3 else ''

            if (property_data.get('caller_phone') and sheet_phone == property_data.get('caller_phone')) or \
               (property_data.get('caller_email') and sheet_email == property_data.get('caller_email')) or \
               (property_data.get('property_address') and sheet_address == property_data.get('property_address')):
                row_index = i
                break

    if row_index:
        # Update existing row
        update_range = f"{worksheet_name}!A{row_index}:L{row_index}"
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=update_range,
            valueInputOption='USER_ENTERED',
            body={'values': [values]},
        ).execute()
        return True
    else:
        # Append new row
        sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{worksheet_name}!A1",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]},
        ).execute()
        return True


def send_urgent_lead_email(lead_data: dict) -> bool:
    admin_email = os.environ.get('ADMIN_EMAIL', '').strip()
    if not admin_email:
        return False

    creds = get_or_refresh_credentials()
    if not creds:
        return False

    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    service = build('gmail', 'v1', credentials=creds)

    message = MIMEMultipart('alternative')
    message['To'] = admin_email
    message['Subject'] = f"Urgent Lead: {lead_data.get('caller_name', 'New Lead')}"

    html_body = f"""
    <html>
      <body>
        <h2>Urgent Lead Notification</h2>
        <table style="border-collapse: collapse; width: 100%;">
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Caller Name</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{lead_data.get('caller_name', 'N/A')}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Phone</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{lead_data.get('caller_phone', 'N/A')}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Email</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{lead_data.get('caller_email', 'N/A')}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Property Address</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{lead_data.get('property_address', 'N/A')}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Priority</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: red; font-weight: bold;">{lead_data.get('call_priority', 'N/A')}</td></tr>
        </table>
        <p style="margin-top: 16px;">This lead has been automatically synced to Google Sheets.</p>
      </body>
    </html>
    """

    text_body = f"""
Urgent Lead Notification

Caller Name: {lead_data.get('caller_name', 'N/A')}
Phone: {lead_data.get('caller_phone', 'N/A')}
Email: {lead_data.get('caller_email', 'N/A')}
Property Address: {lead_data.get('property_address', 'N/A')}
Priority: {lead_data.get('call_priority', 'N/A')}

This lead has been automatically synced to Google Sheets.
    """

    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    message.attach(part1)
    message.attach(part2)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    try:
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        return True
    except Exception:
        return False
