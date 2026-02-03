from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User

class Command(BaseCommand):
    help = 'Initialize Groups and Permissions based on User Roles'

    def handle(self, *args, **options):
        self.stdout.write("Initializing Groups and Permissions...")

        # 1. Define Role -> Permissions Mapping
        # Keys are Role values from User.Roles
        # Values are lists of codenames (Permissions)
        role_permissions = {
            # Broker Team
            User.Roles.BROKER_ADMIN: [
                'view_broker_dashboard', 
                'manage_users',
                # Add standard Django perms if needed, e.g., 'add_user', 'change_user'
            ],
            User.Roles.BROKER_STAFF: [
                'view_broker_dashboard',
            ],

            # HR Team
            User.Roles.HR_ADMIN: [
                'view_hr_dashboard',
                'manage_users',
            ],
            User.Roles.HR_STAFF: [
                'view_hr_dashboard',
            ],

            # Partners
            User.Roles.PHARMACIST: [
                'view_partner_dashboard',
            ],
            User.Roles.CHRONIC_ADMIN: [
                'view_partner_dashboard',
                'manage_users',
            ],
            User.Roles.CHRONIC_STAFF: [
                'view_partner_dashboard',
            ],

            # Viewers / Members
            User.Roles.VIEWER: [],
            User.Roles.MEMBER: [], # Members usually valid just by being logged in, or specific perms
        }

        # 2. Setup Groups and Assign Permissions
        for role, perms in role_permissions.items():
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(f"Created Group: {role}")
            else:
                self.stdout.write(f"Group exists: {role}")

            # Clear existing perms to ensure state matches config
            group.permissions.clear()

            for codename in perms:
                try:
                    permission = Permission.objects.get(codename=codename)
                    group.permissions.add(permission)
                    self.stdout.write(f"  + Added permission: {codename}")
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  ! Permission not found: {codename}"))

        # 3. Sync Existing Users
        self.stdout.write("\nSyncing existing users to groups...")
        users = User.objects.all()
        for user in users:
            # We can trigger the signal by calling save()
            # Or manually call the logic to be faster/safer without triggering other side effects
            # calling save() is safer to ensure consistency with the signal we just wrote.
            user.save()
            self.stdout.write(f"  Synced user: {user.username} -> {user.role}")

        self.stdout.write(self.style.SUCCESS("Successfully initialized Groups and Permissions."))
