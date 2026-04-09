import json

from django.utils import timezone

from channels.generic.websocket import AsyncWebsocketConsumer

from ember_apps.leads.google_sheets import append_lead_row, send_urgent_lead_email, append_normal_lead_row
from ember_apps.leads.models import Lead

from .models import Call, TranscriptEvent


class TranscriptConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope["url_route"]["kwargs"]["call_id"]
        self.group_name = f"transcript_{self.call_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def transcript_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))


class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        call = await Call.objects.acreate(started_at=timezone.now(), status='in_progress')
        self.call_id = str(call.id)
        self.group_name = f"transcript_{self.call_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "session",
                    "call_id": self.call_id,
                }
            )
        )

    async def disconnect(self, close_code):
        await Call.objects.filter(id=self.call_id, ended_at__isnull=True).aupdate(
            ended_at=timezone.now(),
            status='completed',
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                msg = json.loads(text_data)
            except json.JSONDecodeError:
                return

            if msg.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
                return

            if msg.get("type") == "bind" and msg.get("vapi_call_id"):
                vapi_call_id = str(msg.get("vapi_call_id"))
                await Call.objects.filter(id=self.call_id).aupdate(vapi_call_id=vapi_call_id)
                await self.send(text_data=json.dumps({"type": "bound", "call_id": self.call_id}))
                return

            if msg.get("type") == "persist_transcript":
                role = str(msg.get("role") or "unknown")
                text = str(msg.get("text") or "").strip()
                occurred_at_raw = msg.get("occurred_at")
                occurred_at = None
                if isinstance(occurred_at_raw, str) and occurred_at_raw.strip():
                    try:
                        from django.utils.dateparse import parse_datetime

                        occurred_at = parse_datetime(occurred_at_raw)
                    except Exception:
                        occurred_at = None

                if text:
                    await TranscriptEvent.objects.acreate(
                        call_id=self.call_id,
                        role=role,
                        text=text,
                        occurred_at=occurred_at,
                    )
                return

            if msg.get("type") == "persist_lead" and isinstance(msg.get("lead"), dict):
                lead = msg.get("lead") or {}

                caller_name = str(
                    lead.get("caller_name")
                    or lead.get("customer_name")
                    or lead.get("name")
                    or ""
                ).strip()
                caller_phone = str(
                    lead.get("caller_phone")
                    or lead.get("phone")
                    or lead.get("phone_number")
                    or ""
                ).strip()
                caller_email = str(lead.get("caller_email") or lead.get("email") or "").strip()

                if caller_name and caller_phone and caller_email:
                    call_priority = str(lead.get("call_priority") or "").strip()
                    defaults = {
                        "call_reason": str(lead.get("call_reason") or "").strip(),
                        "call_priority": call_priority,
                        "property_address": str(lead.get("property_address") or "").strip(),
                        "occupancy_status": str(lead.get("occupancy_status") or "").strip(),
                        "sell_timeframe": str(lead.get("sell_timeframe") or lead.get("sell_timeline") or "").strip(),
                        "additional_notes": str(lead.get("additional_notes") or "").strip(),
                        "intent": str(lead.get("intent") or "").strip(),
                        "query_description": str(lead.get("query_description") or "").strip(),
                        "update_topic": str(lead.get("update_topic") or "").strip(),
                    }

                    lead_obj, created = await Lead.objects.aget_or_create(
                        call_id=self.call_id,
                        caller_name=caller_name,
                        caller_phone=caller_phone,
                        caller_email=caller_email,
                        defaults=defaults,
                    )
                    if created:
                        import asyncio
                        if call_priority.lower() == "urgent":
                            await asyncio.to_thread(
                                append_lead_row,
                                [
                                    lead_obj.caller_name,
                                    lead_obj.caller_phone,
                                    lead_obj.caller_email,
                                    lead_obj.property_address,
                                    lead_obj.sell_timeframe,
                                    lead_obj.occupancy_status,
                                    lead_obj.call_reason,
                                    lead_obj.call_priority,
                                    lead_obj.additional_notes,
                                    lead_obj.created_at.isoformat(),
                                ],
                            )
                            await asyncio.to_thread(
                                send_urgent_lead_email,
                                {
                                    'caller_name': lead_obj.caller_name,
                                    'caller_phone': lead_obj.caller_phone,
                                    'caller_email': lead_obj.caller_email,
                                    'property_address': lead_obj.property_address,
                                    'call_priority': lead_obj.call_priority,
                                },
                            )
                        else:
                            await asyncio.to_thread(
                                append_normal_lead_row,
                                {
                                    'caller_name': lead_obj.caller_name,
                                    'caller_phone': lead_obj.caller_phone,
                                    'caller_email': lead_obj.caller_email,
                                    'property_address': lead_obj.property_address,
                                    'sell_timeframe': lead_obj.sell_timeframe,
                                    'occupancy_status': lead_obj.occupancy_status,
                                    'call_reason': lead_obj.call_reason,
                                    'call_priority': lead_obj.call_priority,
                                    'additional_notes': lead_obj.additional_notes,
                                    'created_at': lead_obj.created_at.isoformat() if lead_obj.created_at else '',
                                },
                            )
                return

        if bytes_data:
            return

    async def transcript_event(self, event):
        payload = event.get("payload") or {}
        await self.send(
            text_data=json.dumps(
                {
                    "type": "transcript_event",
                    **payload,
                }
            )
        )
