# Generated manually for Twilio integration

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('calls', '0004_drop_vapi_assistant_and_agent_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='call',
            name='direction',
            field=models.CharField(
                choices=[('web', 'Web Browser'), ('inbound', 'Inbound Phone'), ('outbound', 'Outbound Phone')],
                default='web',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='call',
            name='phone_number',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='call',
            name='twilio_call_sid',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
