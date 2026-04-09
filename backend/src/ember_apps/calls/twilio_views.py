"""
Twilio integration views for inbound/outbound phone calls.
These connect Twilio to Vapi AI for voice conversations.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Sip, Gather

from ember_apps.calls.models import Call
from ember_apps.calls.serializers import CallSerializer


def get_twilio_client() -> Client | None:
    """Get Twilio client if credentials are configured."""
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not account_sid or not auth_token:
        return None
    return Client(account_sid, auth_token)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_outbound_call(request):
    """
    Initiate an outbound call to a phone number.
    The call will connect to Vapi AI for conversation.
    """
    phone_number = request.data.get('phone_number', '').strip()

    print(f">>> initiate_outbound_call: phone={phone_number}, user={request.user}")

    if not phone_number:
        return Response(
            {'error': 'Phone number is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Normalize phone number (basic E.164 format check)
    if not phone_number.startswith('+'):
        return Response(
            {'error': 'Phone number must be in E.164 format (e.g., +1234567890)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    client = get_twilio_client()
    if not client:
        return Response(
            {'error': 'Twilio is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    # Create call record in database
    call = Call.objects.create(
        direction='outbound',
        phone_number=phone_number,
        status='initiated',
        started_at=timezone.now(),
    )
    
    try:
        # Build webhook URLs - force HTTPS for Twilio webhooks
        # Cloudflare sends X-Forwarded-Proto header
        host = request.get_host()
        forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO')
        scheme = 'https' if (request.is_secure() or forwarded_proto == 'https') else 'http'
        # Always use HTTPS for production webhooks
        if 'propstarportal.com' in host:
            scheme = 'https'
        base_url = f'{scheme}://{host}'
        
        # Create Twilio call
        # TEMPORARY: Use static test endpoint to verify Twilio can reach webhook
        voice_url = f'{base_url}/api/twilio/test-voice/'
        # Normal URL: f'{base_url}/api/twilio/voice-stream/{call.id}/'
        status_url = f'{base_url}/api/twilio/status/'

        print(f">>> Creating Twilio call:")
        print(f"    to: {phone_number}")
        print(f"    from: {settings.TWILIO_PHONE_NUMBER}")
        print(f"    voice_url: {voice_url} (STATIC TEST URL)")
        print(f"    status_url: {status_url}")

        twilio_call = client.calls.create(
            to=phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=voice_url,
            status_callback=status_url,
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
        )

        print(f">>> Twilio call created: SID={twilio_call.sid}")

        # Update call record with Twilio SID
        call.twilio_call_sid = twilio_call.sid
        call.status = 'initiated'
        call.save(update_fields=['twilio_call_sid', 'status'])

        return Response({
            'call_id': str(call.id),
            'twilio_call_sid': twilio_call.sid,
            'status': 'initiated',
            'phone_number': phone_number,
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f">>> ERROR creating Twilio call: {e}")
        import traceback
        traceback.print_exc()
        call.status = 'failed'
        call.save(update_fields=['status'])
        return Response(
            {'error': f'Failed to create call: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def twilio_voice_stream(request, call_id: str):
    """
    Return TwiML that connects the call to Vapi AI via SIP.
    This is called by Twilio when the call is answered.
    """
    # Log the webhook hit for debugging
    print(f"=" * 60)
    print(f"Twilio webhook HIT: voice_stream")
    print(f"Call ID: {call_id}")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Request data: {request.data}")
    print(f"Query params: {request.query_params}")
    print(f"META: {request.META.get('HTTP_HOST')}, {request.META.get('REMOTE_ADDR')}")
    print(f"=" * 60)

    # TEMPORARY: Force test mode to debug webhook - set to False to use real Vapi
    FORCE_TEST_MODE = True

    # Check for test mode - add ?test=1 to URL to force simple response
    if FORCE_TEST_MODE or request.query_params.get('test') == '1' or request.data.get('test') == '1':
        print("TEST MODE: Returning simple Say response (Vapi connection bypassed)")
        response = VoiceResponse()
        response.say('Test successful. Your webhook is working. Goodbye.')
        response.hangup()
        return Response(str(response), content_type='application/xml')

    # Update call status
    try:
        call = Call.objects.get(id=call_id)
        call.status = 'answered'
        call.save(update_fields=['status'])
    except Call.DoesNotExist:
        print(f"Warning: Call {call_id} not found in database")

    response = VoiceResponse()
    
    # Connect to Vapi AI using SIP
    sip_username = settings.VAPI_SIP_USERNAME
    sip_password = settings.VAPI_SIP_PASSWORD
    
    if sip_username and sip_password:
        # Use Vapi SIP endpoint with authentication
        # Twilio requires username/password as separate attributes
        dial = Dial()
        sip = Sip('sip:sip.vapi.ai', username=sip_username, password=sip_password)
        dial.append(sip)
        response.append(dial)
    else:
        # Fallback: say a message and hang up if no SIP configured
        response.say('Voice agent is not configured. Please contact support.')
        response.hangup()
    
    return Response(str(response), content_type='application/xml')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def twilio_status_callback(request):
    """
    Handle Twilio status callbacks for call state changes.
    Twilio sends these as GET requests by default.
    """
    # Log all status callbacks
    print(f"-" * 60)
    print(f"Twilio STATUS CALLBACK: {request.method}")
    if request.method == 'GET':
        print(f"Query params: {request.query_params}")
    else:
        print(f"POST data: {request.data}")
    print(f"-" * 60)

    # Handle both GET (query params) and POST (form data) requests
    if request.method == 'GET':
        call_sid = request.query_params.get('CallSid')
        call_status = request.query_params.get('CallStatus')
    else:
        call_sid = request.data.get('CallSid')
        call_status = request.data.get('CallStatus')
    
    if not call_sid:
        return Response({'ok': True})
    
    try:
        call = Call.objects.get(twilio_call_sid=call_sid)
        
        # Map Twilio status to our status
        status_map = {
            'queued': 'queued',
            'ringing': 'ringing',
            'in-progress': 'in_progress',
            'completed': 'completed',
            'busy': 'busy',
            'failed': 'failed',
            'no-answer': 'no_answer',
            'canceled': 'canceled',
        }
        
        call.status = status_map.get(call_status, call_status)
        
        if call_status in ['completed', 'busy', 'failed', 'no-answer', 'canceled']:
            call.ended_at = timezone.now()
        
        call.save(update_fields=['status', 'ended_at'])
        
    except Call.DoesNotExist:
        pass
    
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_call_status(request, call_id: str):
    """
    Get the current status of a call.
    """
    try:
        call = Call.objects.get(id=call_id)
        serializer = CallSerializer(call)
        return Response(serializer.data)
    except Call.DoesNotExist:
        return Response(
            {'error': 'Call not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_call(request, call_id: str):
    """
    End an active call.
    """
    try:
        call = Call.objects.get(id=call_id, direction='outbound')
        
        if call.twilio_call_sid and not call.ended_at:
            client = get_twilio_client()
            if client:
                try:
                    client.calls(call.twilio_call_sid).update(status='completed')
                except Exception:
                    pass
        
        call.status = 'completed'
        call.ended_at = timezone.now()
        call.save(update_fields=['status', 'ended_at'])
        
        return Response({'ok': True})

    except Call.DoesNotExist:
        return Response(
            {'error': 'Call not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def test_voice_webhook(request):
    """
    Simple test endpoint that always returns a working TwiML response.
    Use this to verify Twilio can reach your server.
    """
    print(f"=" * 60)
    print(f"TEST WEBHOOK HIT: {request.method}")
    print(f"Path: {request.path}")
    print(f"Query params: {request.query_params}")
    print(f"Data: {request.data}")
    print(f"Headers: {dict(request.headers)}")
    print(f"=" * 60)

    from twilio.twiml.voice_response import VoiceResponse
    response = VoiceResponse()
    response.say('This is a test. Your webhook is working correctly. Goodbye.')
    response.hangup()

    return Response(str(response), content_type='application/xml')
