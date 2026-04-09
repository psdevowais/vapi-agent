from django.db import models


class Lead(models.Model):
    INTENT_CHOICES = [
        ('sell', 'Sell'),
        ('update', 'Update'),
        ('unclear', 'Unclear/Other'),
    ]

    call = models.ForeignKey(
        'calls.Call',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    caller_name = models.CharField(max_length=255)
    caller_phone = models.CharField(max_length=64)
    caller_email = models.EmailField()
    call_reason = models.CharField(max_length=32, blank=True, default='')
    call_priority = models.CharField(max_length=32, blank=True, default='')
    property_address = models.TextField(blank=True, default='')
    occupancy_status = models.CharField(max_length=32, blank=True, default='')
    sell_timeframe = models.CharField(max_length=128, blank=True, default='')
    additional_notes = models.TextField(blank=True, default='')
    intent = models.CharField(max_length=32, blank=True, default='', choices=INTENT_CHOICES)
    query_description = models.TextField(blank=True, default='')
    update_topic = models.CharField(max_length=128, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Property(models.Model):
    caller_name = models.CharField(max_length=255, blank=True, default='')
    caller_phone = models.CharField(max_length=64, blank=True, default='')
    caller_email = models.EmailField(blank=True, default='')
    property_address = models.TextField(blank=True, default='')
    property_status = models.CharField(max_length=64, blank=True, default='')
    sell_timeframe = models.CharField(max_length=128, blank=True, default='')
    price_listing = models.CharField(max_length=64, blank=True, default='')
    occupancy_status = models.CharField(max_length=32, blank=True, default='')
    call_priority = models.CharField(max_length=32, blank=True, default='')
    call_reason = models.CharField(max_length=32, blank=True, default='')
    additional_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['caller_phone']),
            models.Index(fields=['caller_email']),
            models.Index(fields=['property_address']),
        ]

    def __str__(self):
        return f"{self.caller_name} - {self.property_address}"

# Create your models here.
