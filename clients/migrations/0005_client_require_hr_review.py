from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0004_client_broker'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='require_hr_review',
            field=models.BooleanField(
                default=False,
                help_text='If enabled, service requests submitted by members will be reviewed by HR before being forwarded to the broker.',
                verbose_name='Require HR Review for Service Requests',
            ),
        ),
    ]
