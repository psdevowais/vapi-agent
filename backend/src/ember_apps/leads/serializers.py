from rest_framework import serializers

from .models import Lead, Property


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id',
            'call',
            'caller_name',
            'caller_phone',
            'caller_email',
            'call_reason',
            'call_priority',
            'property_address',
            'occupancy_status',
            'sell_timeframe',
            'additional_notes',
            'intent',
            'query_description',
            'update_topic',
            'created_at',
        ]


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            'id',
            'caller_name',
            'caller_phone',
            'caller_email',
            'property_address',
            'property_status',
            'sell_timeframe',
            'price_listing',
            'occupancy_status',
            'call_priority',
            'call_reason',
            'additional_notes',
            'created_at',
            'updated_at',
        ]
