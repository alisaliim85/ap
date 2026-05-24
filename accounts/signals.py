from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import User

@receiver(post_save, sender=User)
def move_user_to_group(sender, instance, created, **kwargs):
    """
    Sync User Role -> Django Group.
    When a user is saved, remove them from all other 'Role' groups and add them to the one matching their new role.
    Groups must already exist (created via data migration). This signal will NOT create new groups.
    """
    if not instance.role:
        return

    group_name = instance.role
    all_role_names = [choice[0] for choice in User.Roles.choices]

    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return

    if not instance.groups.filter(pk=group.pk).exists():
        instance.groups.add(group)

    groups_to_remove = instance.groups.filter(name__in=all_role_names).exclude(pk=group.pk)
    if groups_to_remove.exists():
        instance.groups.remove(*groups_to_remove)
