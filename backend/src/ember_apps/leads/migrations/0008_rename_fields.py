from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0007_add_property_model'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lead',
            old_name='customer_name',
            new_name='caller_name',
        ),
        migrations.RenameField(
            model_name='lead',
            old_name='phone',
            new_name='caller_phone',
        ),
        migrations.RenameField(
            model_name='lead',
            old_name='email',
            new_name='caller_email',
        ),
        migrations.RenameField(
            model_name='lead',
            old_name='sell_timeline',
            new_name='sell_timeframe',
        ),
        migrations.AddField(
            model_name='lead',
            name='query_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='lead',
            name='update_topic',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.RenameField(
            model_name='property',
            old_name='customer_name',
            new_name='caller_name',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='phone',
            new_name='caller_phone',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='email',
            new_name='caller_email',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='sell_timeline',
            new_name='sell_timeframe',
        ),
    ]
