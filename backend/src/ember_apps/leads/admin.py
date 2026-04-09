from django.contrib import admin

from .models import Lead
from .oauth_models import GoogleOAuthToken


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['caller_name', 'caller_phone', 'caller_email', 'property_address', 'call_priority', 'created_at']
    list_filter = ['call_priority', 'created_at']
    search_fields = ['caller_name', 'caller_phone', 'caller_email', 'property_address']


@admin.register(GoogleOAuthToken)
class GoogleOAuthTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
