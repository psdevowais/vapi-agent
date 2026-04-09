from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ember_apps.leads.google_sheets import append_lead_row, send_urgent_lead_email, append_normal_lead_row
from ember_apps.leads.models import Lead, Property
from ember_apps.leads.serializers import PropertySerializer

from .models import Call, TranscriptEvent
from .serializers import (
    CallDetailSerializer,
    CallListSerializer,
    CallSerializer,
)


class CallListCreateView(generics.ListCreateAPIView):
    queryset = Call.objects.all()

    def get_queryset(self):
        return (
            Call.objects.all()
            .annotate(
                transcript_event_count=Count('transcript_events', distinct=True),
                lead_count=Count('leads', distinct=True),
            )
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CallListSerializer
        return CallSerializer


class CallDetailView(generics.RetrieveAPIView):
    queryset = Call.objects.all()
    serializer_class = CallDetailSerializer


class AnalyticsView(APIView):
    def get(self, request):
        today = now().date()
        seven_days_ago = today - timedelta(days=7)
        thirty_days_ago = today - timedelta(days=30)

        total_calls = Call.objects.count()
        calls_by_status = list(
            Call.objects.values('status').annotate(count=Count('id')).order_by('status')
        )

        calls_today = Call.objects.filter(created_at__date=today).count()
        calls_this_week = Call.objects.filter(created_at__date__gte=seven_days_ago).count()
        calls_this_month = Call.objects.filter(created_at__date__gte=thirty_days_ago).count()

        urgent_leads = Lead.objects.filter(call_priority__iexact='urgent').count()
        normal_leads = Lead.objects.exclude(call_priority__iexact='urgent').count()

        return Response(
            {
                'total_calls': total_calls,
                'calls_by_status': calls_by_status,
                'calls_today': calls_today,
                'calls_this_week': calls_this_week,
                'calls_this_month': calls_this_month,
                'urgent_leads': urgent_leads,
                'normal_leads': normal_leads,
            }
        )


class VapiWebhookView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request):
        payload = request.data

        raw_call_id = (
            payload.get('call_id')
            or payload.get('callId')
            or payload.get('call', {}).get('id')
        )
        if not raw_call_id:
            return Response({'detail': 'Missing callId'}, status=status.HTTP_400_BAD_REQUEST)

        call: Call
        try:
            call_uuid = UUID(str(raw_call_id))
            call, _ = Call.objects.get_or_create(id=call_uuid)
        except ValueError:
            call, _ = Call.objects.get_or_create(vapi_call_id=str(raw_call_id))

        if payload.get('call', {}).get('id') and not call.vapi_call_id:
            call.vapi_call_id = payload['call']['id']
        if payload.get('status'):
            call.status = payload['status']

        call.save(update_fields=['vapi_call_id', 'status', 'updated_at'])

        message = payload.get('message') or payload
        event_type = message.get('type') if isinstance(message, dict) else None

        transcript_text = None
        transcript_role = None
        occurred_at: datetime | None = None

        lead_data: dict[str, Any] | None = None

        if isinstance(message, dict):
            if message.get('timestamp'):
                occurred_at = parse_datetime(message.get('timestamp'))
            if event_type in {'transcript', 'transcript-update'}:
                transcript_role = message.get('role') or message.get('speaker') or 'unknown'
                transcript = message.get('transcript')
                if isinstance(transcript, dict):
                    transcript_text = transcript.get('text') or transcript.get('transcript')
                    transcript_role = transcript.get('role') or transcript_role
                else:
                    transcript_text = transcript or message.get('text')
            elif event_type == 'add-message' and isinstance(message.get('message'), dict):
                transcript_text = message['message'].get('content')
                transcript_role = message['message'].get('role')

            tool = message.get('tool') or message.get('function')
            if isinstance(tool, dict):
                name = tool.get('name') or tool.get('tool') or tool.get('function')
                args = tool.get('arguments') or tool.get('args')
                if isinstance(name, str) and name.lower() in {'save_lead', 'savelead', 'lead', 'save-lead'}:
                    if isinstance(args, dict):
                        lead_data = args

            tool_calls = message.get('toolCalls') or message.get('tool_calls')
            if isinstance(tool_calls, list) and not lead_data:
                for item in tool_calls:
                    if not isinstance(item, dict):
                        continue
                    fn = item.get('function')
                    if not isinstance(fn, dict):
                        continue
                    name = fn.get('name')
                    args = fn.get('arguments')
                    if isinstance(args, str):
                        try:
                            import json as _json

                            args = _json.loads(args)
                        except Exception:
                            args = None
                    if isinstance(name, str) and name.lower() in {'save_lead', 'savelead', 'lead', 'save-lead'}:
                        if isinstance(args, dict):
                            lead_data = args
                            break

        if transcript_text:
            recent_cutoff = now() - timedelta(seconds=3)
            existing = TranscriptEvent.objects.filter(
                call=call,
                role=transcript_role or 'unknown',
                created_at__gte=recent_cutoff,
            ).order_by('-created_at').first()

            if existing:
                if len(transcript_text) > len(existing.text) or existing.text in transcript_text:
                    existing.text = transcript_text
                    if occurred_at:
                        existing.occurred_at = occurred_at
                    existing.save(update_fields=['text', 'occurred_at', 'updated_at'])
                    event_id = existing.id
                else:
                    event_id = existing.id
            else:
                new_event = TranscriptEvent.objects.create(
                    call=call,
                    role=transcript_role or 'unknown',
                    text=transcript_text,
                    occurred_at=occurred_at,
                )
                event_id = new_event.id

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'transcript_{call.id}',
                {
                    'type': 'transcript.event',
                    'payload': {
                        'id': str(event_id),
                        'call_id': str(call.id),
                        'role': transcript_role or 'unknown',
                        'text': transcript_text,
                        'occurred_at': occurred_at.isoformat() if occurred_at else None,
                    },
                },
            )

        if isinstance(lead_data, dict):
            caller_name = (
                lead_data.get('caller_name')
                or lead_data.get('customer_name')
                or lead_data.get('name')
                or ''
            ).strip()
            caller_phone = (
                lead_data.get('caller_phone')
                or lead_data.get('phone')
                or lead_data.get('phone_number')
                or ''
            ).strip()
            caller_email = (lead_data.get('caller_email') or lead_data.get('email') or '').strip()

            call_reason = (lead_data.get('call_reason') or '').strip()
            call_priority = (lead_data.get('call_priority') or '').strip()
            property_address = (lead_data.get('property_address') or lead_data.get('address') or '').strip()
            occupancy_status = (lead_data.get('occupancy_status') or '').strip()
            sell_timeframe = (lead_data.get('sell_timeframe') or lead_data.get('sell_timeline') or '').strip()
            intent = (lead_data.get('intent') or '').strip()
            additional_notes = (lead_data.get('additional_notes') or '').strip()
            query_description = (lead_data.get('query_description') or '').strip()
            update_topic = (lead_data.get('update_topic') or '').strip()

            if caller_name and caller_phone and caller_email:
                lead, created = Lead.objects.get_or_create(
                    call=call,
                    caller_name=caller_name,
                    caller_phone=caller_phone,
                    caller_email=caller_email,
                    property_address=property_address,
                    call_reason=call_reason,
                    call_priority=call_priority,
                    occupancy_status=occupancy_status,
                    sell_timeframe=sell_timeframe,
                    intent=intent,
                    additional_notes=additional_notes,
                    query_description=query_description,
                    update_topic=update_topic,
                )
                if created:
                    if call_priority.lower() == 'urgent':
                        append_lead_row(
                            [
                                lead.caller_name,
                                lead.caller_phone,
                                lead.caller_email,
                                lead.property_address,
                                lead.sell_timeframe,
                                lead.occupancy_status,
                                lead.call_reason,
                                lead.call_priority,
                                lead.additional_notes,
                                lead.created_at.isoformat(),
                            ]
                        )
                        send_urgent_lead_email({
                            'caller_name': lead.caller_name,
                            'caller_phone': lead.caller_phone,
                            'caller_email': lead.caller_email,
                            'property_address': lead.property_address,
                            'call_priority': lead.call_priority,
                        })
                    else:
                        append_normal_lead_row({
                            'caller_name': lead.caller_name,
                            'caller_phone': lead.caller_phone,
                            'caller_email': lead.caller_email,
                            'property_address': lead.property_address,
                            'sell_timeframe': lead.sell_timeframe,
                            'occupancy_status': lead.occupancy_status,
                            'call_reason': lead.call_reason,
                            'call_priority': lead.call_priority,
                            'additional_notes': lead.additional_notes,
                            'created_at': lead.created_at.isoformat() if lead.created_at else '',
                        })

        return Response({'ok': True})


class LookupInfoView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request):
        payload = request.data
        print(f'===== LOOKUP INFO: INCOMING PAYLOAD =====')
        print(payload)

        tool_call_id = None
        tool_calls = (
            payload.get('message', {}).get('toolCalls')
            or payload.get('message', {}).get('tool_calls')
            or payload.get('toolCalls')
            or payload.get('tool_calls')
        )
        if isinstance(tool_calls, list) and len(tool_calls) > 0:
            item = tool_calls[0]
            tool_call_id = item.get('id') or item.get('toolCallId')
            fn = item.get('function') if isinstance(item, dict) else None
            if isinstance(fn, dict):
                raw_args = fn.get('arguments')
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        pass
                elif isinstance(raw_args, dict):
                    args = raw_args

        if args is None:
            args = payload.get('message', {}) if isinstance(payload.get('message'), dict) else payload

        caller_phone = str(args.get('caller_phone') or args.get('phone') or '').strip()
        caller_email = str(args.get('caller_email') or args.get('email') or '').strip()
        property_address = str(args.get('property_address') or args.get('address') or '').strip()

        print(f'Extracted -> phone: "{caller_phone}", email: "{caller_email}", address: "{property_address}"')

        if not caller_phone and not caller_email and not property_address:
            result_text = 'No identifying information provided. Please ask for name, phone, email, or property address.'
            print(f'===== LOOKUP INFO: RESPONSE (no info) =====')
            print(result_text)
            return Response({
                'results': [
                    {
                        'toolCallId': tool_call_id,
                        'result': result_text,
                    }
                ]
            })

        query = {}
        if caller_phone:
            query['caller_phone__icontains'] = caller_phone
        if caller_email:
            query['caller_email__iexact'] = caller_email
        if property_address:
            query['property_address__icontains'] = property_address

        print(f'Query filters: {query}')

        properties = Property.objects.filter(**query).order_by('-updated_at')[:5]

        print(f'Found {properties.count()} properties')
        for prop in properties:
            print(f'  -> {prop.caller_name} | {prop.caller_phone} | {prop.caller_email} | {prop.property_address}')

        if not properties:
            result_text = f'No property records found matching the provided information.'
            return Response({
                'results': [
                    {
                        'toolCallId': tool_call_id,
                        'result': result_text,
                    }
                ]
            })

        prop = properties.first()

        # Build response with only required fields
        response_data = {
            'caller_name': prop.caller_name,
            'caller_phone': prop.caller_phone,
            'caller_email': prop.caller_email,
            'property_address': prop.property_address,
            'property_status': prop.property_status,
            'occupancy_status': prop.occupancy_status,
            'sell_timeframe': prop.sell_timeframe,
        }

        print(f'===== LOOKUP INFO: RESPONSE =====')
        print(response_data)

        return Response({
            'results': [
                {
                    'toolCallId': tool_call_id,
                    'result': response_data,
                }
            ]
        })
