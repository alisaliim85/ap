from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medications', '0002_alter_medicationcomment_options_and_more'),
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicationrequest',
            name='pharmacy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                limit_choices_to={'is_active': True, 'partner_type': 'PHARMACY_CHAIN'},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='medication_requests',
                to='partners.partner',
                verbose_name='Assigned Pharmacy',
            ),
        ),
    ]
