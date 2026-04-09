from typing import Any

from rest_framework.response import Response
from rest_framework.views import APIView

from .google_sheets import update_property_db_row
from .models import Property


def extract_tool_call_id(payload):
    """Extract toolCallId from VAPI payload."""
    tool_calls = (
        payload.get('message', {}).get('toolCalls')
        or payload.get('message', {}).get('tool_calls')
        or payload.get('toolCalls')
        or payload.get('tool_calls')
    )
    if isinstance(tool_calls, list) and len(tool_calls) > 0:
        item = tool_calls[0]
        return item.get('id') or item.get('toolCallId')
    return None


def extract_args(payload):
    """Extract arguments from VAPI payload."""
    args = None
    tool_calls = (
        payload.get('message', {}).get('toolCalls')
        or payload.get('message', {}).get('tool_calls')
        or payload.get('toolCalls')
        or payload.get('tool_calls')
    )
    if isinstance(tool_calls, list) and len(tool_calls) > 0:
        item = tool_calls[0]
        fn = item.get('function') if isinstance(item, dict) else None
        if isinstance(fn, dict):
            raw_args = fn.get('arguments')
            if isinstance(raw_args, str):
                try:
                    import json
                    args = json.loads(raw_args)
                except Exception:
                    pass
            elif isinstance(raw_args, dict):
                args = raw_args
    if args is None:
        args = payload.get('message', {}) if isinstance(payload.get('message'), dict) else payload
    return args


class VerifyOwnerView(APIView):
    """Verify property owner by matching caller info and returning property details including price."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request):
        payload = request.data
        tool_call_id = extract_tool_call_id(payload)
        args = extract_args(payload)

        caller_phone = str(args.get('caller_phone') or '').strip()
        caller_email = str(args.get('caller_email') or '').strip()
        property_address = str(args.get('property_address') or '').strip()

        if not caller_phone and not caller_email and not property_address:
            result_text = 'No identifying information provided. Please ask for phone, email, or property address.'
            return Response({
                'results': [{'toolCallId': tool_call_id, 'result': result_text}]
            })

        query = {}
        if caller_phone:
            query['caller_phone__icontains'] = caller_phone
        if caller_email:
            query['caller_email__iexact'] = caller_email
        if property_address:
            query['property_address__icontains'] = property_address

        try:
            property_obj = Property.objects.filter(**query).first()
        except Exception:
            property_obj = None

        if not property_obj:
            result_data = {'found': False, 'error': 'Property not found in our records.'}
            return Response({
                'results': [{'toolCallId': tool_call_id, 'result': result_data}]
            })

        # Return ALL property data for VAPI to use
        result_data = {
            'found': True,
            'caller_name': property_obj.caller_name,
            'caller_phone': property_obj.caller_phone,
            'caller_email': property_obj.caller_email,
            'property_address': property_obj.property_address,
            'property_status': property_obj.property_status,
            'sell_timeframe': property_obj.sell_timeframe,
            'price_listing': property_obj.price_listing,
            'occupancy_status': property_obj.occupancy_status,
            'call_priority': property_obj.call_priority,
            'call_reason': property_obj.call_reason,
            'additional_notes': property_obj.additional_notes,
        }

        return Response({
            'results': [{'toolCallId': tool_call_id, 'result': result_data}]
        })


class UpdateInfoView(APIView):
    """Update property information after owner verification."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request):
        payload = request.data
        tool_call_id = extract_tool_call_id(payload)
        args = extract_args(payload)

        caller_phone = str(args.get('caller_phone') or '').strip()
        caller_email = str(args.get('caller_email') or '').strip()
        property_address = str(args.get('property_address') or '').strip()

        if not caller_phone and not caller_email and not property_address:
            result_text = 'No identifying information provided. Please ask for phone, email, or property address.'
            return Response({
                'results': [{'toolCallId': tool_call_id, 'result': result_text}]
            })

        query = {}
        if caller_phone:
            query['caller_phone__icontains'] = caller_phone
        if caller_email:
            query['caller_email__iexact'] = caller_email
        if property_address:
            query['property_address__icontains'] = property_address

        try:
            property_obj = Property.objects.filter(**query).first()
        except Exception:
            property_obj = None

        if not property_obj:
            result_text = 'Property not found in our records.'
            return Response({
                'results': [{'toolCallId': tool_call_id, 'result': result_text}]
            })

        # Update fields if provided
        updated = []

        if 'occupancy_status' in args:
            property_obj.occupancy_status = str(args.get('occupancy_status') or '').strip()
            updated.append('occupancy status')

        if 'sell_timeframe' in args:
            property_obj.sell_timeframe = str(args.get('sell_timeframe') or '').strip()
            updated.append('selling timeframe')

        if 'property_status' in args:
            property_obj.property_status = str(args.get('property_status') or '').strip()
            updated.append('property status')

        if 'price_listing' in args:
            property_obj.price_listing = str(args.get('price_listing') or '').strip()
            updated.append('listing price')

        if 'call_priority' in args:
            property_obj.call_priority = str(args.get('call_priority') or '').strip()
            updated.append('priority')

        if 'additional_notes' in args:
            property_obj.additional_notes = str(args.get('additional_notes') or '').strip()
            updated.append('notes')

        if 'call_reason' in args:
            property_obj.call_reason = str(args.get('call_reason') or '').strip()

        property_obj.save(update_fields=[
            'occupancy_status', 'sell_timeframe', 'property_status', 'price_listing',
            'call_priority', 'additional_notes', 'call_reason', 'updated_at'
        ] if updated else ['updated_at'])

        # Sync to Google Sheets Property DB
        from django.utils import timezone
        update_property_db_row({
            'caller_name': property_obj.caller_name,
            'caller_phone': property_obj.caller_phone,
            'caller_email': property_obj.caller_email,
            'property_address': property_obj.property_address,
            'property_status': property_obj.property_status,
            'sell_timeframe': property_obj.sell_timeframe,
            'price_listing': property_obj.price_listing,
            'occupancy_status': property_obj.occupancy_status,
            'call_priority': property_obj.call_priority,
            'call_reason': property_obj.call_reason,
            'additional_notes': property_obj.additional_notes,
            'updated_at': timezone.now().isoformat(),
        })

        if updated:
            result_text = f"Successfully updated {', '.join(updated)} for {property_obj.caller_name}'s property."
        else:
            result_text = f"No updates were made to {property_obj.caller_name}'s property."

        return Response({
            'results': [{'toolCallId': tool_call_id, 'result': result_text}]
        })

