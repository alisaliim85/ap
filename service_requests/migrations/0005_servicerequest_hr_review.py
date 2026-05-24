from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service_requests', '0004_assign_permissions_to_groups'),
    ]

    operations = [
        # إضافة حقل hr_note
        migrations.AddField(
            model_name='servicerequest',
            name='hr_note',
            field=models.TextField(blank=True, verbose_name='HR Note'),
        ),
        # تحديث choices لحقل status (إضافة HR_REVIEW)
        migrations.AlterField(
            model_name='servicerequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('SUBMITTED', 'Submitted'),
                    ('HR_REVIEW', 'HR Review'),
                    ('IN_REVIEW', 'In Review'),
                    ('RETURNED', 'Returned (Needs More Info)'),
                    ('RESOLVED', 'Resolved'),
                    ('REJECTED', 'Rejected'),
                    ('TRANSFERRED_TO_MEDICATIONS', 'Transferred to Medications Dept'),
                ],
                db_index=True,
                default='DRAFT',
                max_length=50,
                verbose_name='Status',
            ),
        ),
        # إضافة صلاحية can_process_hr_request
        migrations.AlterModelOptions(
            name='servicerequest',
            options={
                'ordering': ['-created_at'],
                'permissions': [
                    ('can_submit_service_request', 'Can submit new service request'),
                    ('can_process_service_request', 'Can process/resolve service request as Broker'),
                    ('can_process_hr_request', 'Can review/forward service requests as HR'),
                ],
                'verbose_name': 'Service Request',
                'verbose_name_plural': 'Service Requests',
            },
        ),
    ]
