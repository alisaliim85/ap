from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import User

@receiver(post_save, sender=User)
def move_user_to_group(sender, instance, created, **kwargs):
    """
    Sync User Role -> Django Group.
    When a user is saved, remove them from all other 'Role' groups and add them to the one matching their new role.
    """
    if not instance.role:
        return

    # 1. Get or Create the group for this role
    # The group name should match the role value (e.g., 'HR_ADMIN')
    # or the readable label. Let's stick to the Role Value for technical mapping.
    group_name = instance.role
    group, _ = Group.objects.get_or_create(name=group_name)

    # 2. Check if user is already in this group
    if not instance.groups.filter(name=group_name).exists():
        # 3. Add to new group
        instance.groups.add(group)

    # 4. Remove from other groups that correspond to Roles
    # We want to enforce 1 Role = 1 Group mapping, but we shouldn't touch groups unrelated to roles if any exist.
    # However, for now, we assume all groups in the system are Role-based.
    # If we want to be safe, we only remove groups that are IN the User.Roles choices.
    
    all_role_names = [choice[0] for choice in User.Roles.choices]
    
    # Groups the user is in, EXCLUDING the one we just added/verified
    groups_to_remove = instance.groups.filter(name__in=all_role_names).exclude(name=group_name)
    
    if groups_to_remove.exists():
        instance.groups.remove(*groups_to_remove)
