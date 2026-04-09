import uuid

from django.db import models


class Call(models.Model):
    DIRECTION_CHOICES = [
        ('web', 'Web Browser'),
        ('inbound', 'Inbound Phone'),
        ('outbound', 'Outbound Phone'),
    ]

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    vapi_call_id = models.CharField(max_length=128, blank=True, default='')
    twilio_call_sid = models.CharField(max_length=64, blank=True, default='')
    phone_number = models.CharField(max_length=32, blank=True, default='')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='web')
    status = models.CharField(max_length=32, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class TranscriptEvent(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='transcript_events')
    role = models.CharField(max_length=32)
    text = models.TextField()
    occurred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
