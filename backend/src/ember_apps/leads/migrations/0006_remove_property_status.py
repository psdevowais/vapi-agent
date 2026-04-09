# Generated manually to remove property_status field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0005_update_lead_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE leads_lead DROP COLUMN IF EXISTS property_status;',
            reverse_sql='ALTER TABLE leads_lead ADD COLUMN property_status VARCHAR(32) NOT NULL DEFAULT \'\';'
        ),
    ]
