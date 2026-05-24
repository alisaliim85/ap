from django.db import migrations


HR_ROLES = ['SUPER_ADMIN', 'HR_ADMIN', 'HR_STAFF']


def assign_hr_permission(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        perm = Permission.objects.get(
            codename='can_process_hr_request',
            content_type__app_label='service_requests',
        )
    except Permission.DoesNotExist:
        return

    for role_name in HR_ROLES:
        try:
            group = Group.objects.get(name=role_name)
            group.permissions.add(perm)
        except Group.DoesNotExist:
            pass


def remove_hr_permission(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        perm = Permission.objects.get(
            codename='can_process_hr_request',
            content_type__app_label='service_requests',
        )
    except Permission.DoesNotExist:
        return

    for role_name in HR_ROLES:
        try:
            group = Group.objects.get(name=role_name)
            group.permissions.remove(perm)
        except Group.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('service_requests', '0005_servicerequest_hr_review'),
    ]

    operations = [
        migrations.RunPython(assign_hr_permission, remove_hr_permission),
    ]
