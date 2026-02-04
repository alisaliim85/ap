from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup global permissions and migrate users to groups'

    def handle(self, *args, **options):
        self.stdout.write("Starting permission setup...")
        
        with transaction.atomic():
            # 1. Create Groups
            groups_config = {
                'Super Admin': [], # Gets all permissions via is_superuser, but we can give them specific group too
                'Broker Admin': [
                    # Accounts
                    'view_broker_dashboard', 'manage_users',
                    # Clients
                    'view_client_dashboard', 'manage_clients', 'add_client', 'change_client', 'delete_client', 'view_client',
                    # Members
                    'view_member', 'add_member', 'change_member', 'delete_member',
                    # Policies
                    'view_policy', 'add_policy', 'change_policy', 'delete_policy',
                    # Networks
                    'view_network', 'add_network', 'change_network', 'delete_network',
                    'view_serviceprovider', 'add_serviceprovider', 'change_serviceprovider', 'delete_serviceprovider',
                    # Partners
                    'view_partner', 'add_partner', 'change_partner', 'delete_partner',
                    # Providers (Insurance Companies)
                    'view_provider', 'add_provider', 'change_provider', 'delete_provider',
                    # Claims
                    'view_claim', 'change_claim', 'can_process_broker', 'can_view_all_claims',
                ],
                'Broker Staff': [
                    'view_broker_dashboard', 
                    'view_client_dashboard', 'view_client',
                    'view_member',
                    'view_policy',
                    'view_network', 'view_serviceprovider',
                    'view_partner',
                    'view_provider',
                    'view_claim', 'can_view_all_claims',
                ],
                'HR Admin': [
                    'view_hr_dashboard', 
                    'can_submit_claim', 'can_approve_hr', 'can_reject_hr',
                ],
                'HR Staff': [
                    'view_hr_dashboard',
                    'can_submit_claim',
                ],
                'Partner Pharmacist': [
                    'view_partner_dashboard',
                ],
                'Partner Chronic': [
                    'view_partner_dashboard',
                ],
                'Viewer': [
                    # Read only access if needed
                ]
            }

            for group_name, perms in groups_config.items():
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    self.stdout.write(f"Created group: {group_name}")
                
                # Clear existing perms to reset state/ensure correctness
                group.permissions.clear()
                
                for perm_codename in perms:
                    try:
                        # Try to find permission by codename regardless of content type first
                        # Ideally we should specify content type but for simplicity in this script we look it up
                        # Caveat: if multiple apps have same codename (unlikely for standard ones), might be ambiguous.
                        # For 'view_client_dashboard' checks, they are custom permissions on specific models.
                        
                        permission = Permission.objects.filter(codename=perm_codename).first()
                        if permission:
                            group.permissions.add(permission)
                        else:
                            self.stdout.write(self.style.WARNING(f"Permission not found: {perm_codename}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error adding permission {perm_codename}: {e}"))
            
            self.stdout.write(self.style.SUCCESS("Groups and Permissions configured."))

            # 2. Migrate Users
            users = User.objects.all()
            for user in users:
                # Reset flags
                user.is_superuser = False
                user.is_staff = False
                user.groups.clear()

                if user.role == User.Roles.SUPER_ADMIN:
                    user.is_superuser = True
                    user.is_staff = True
                    group = Group.objects.get(name='Super Admin')
                    user.groups.add(group)
                    
                elif user.role == User.Roles.BROKER_ADMIN:
                    user.is_staff = True # Needed to access some admin/staff views if any, but mainly for consistent property
                    group = Group.objects.get(name='Broker Admin')
                    user.groups.add(group)
                    
                elif user.role == User.Roles.BROKER_STAFF:
                    user.is_staff = True
                    group = Group.objects.get(name='Broker Staff')
                    user.groups.add(group)
                    
                elif user.role == User.Roles.HR_ADMIN:
                    group = Group.objects.get(name='HR Admin')
                    user.groups.add(group)
                    
                elif user.role == User.Roles.HR_STAFF:
                    group = Group.objects.get(name='HR Staff')
                    user.groups.add(group)
                
                elif user.role == User.Roles.PHARMACIST:
                    group = Group.objects.get(name='Partner Pharmacist')
                    user.groups.add(group)

                elif user.role in [User.Roles.CHRONIC_ADMIN, User.Roles.CHRONIC_STAFF]:
                     group = Group.objects.get(name='Partner Chronic')
                     user.groups.add(group)
                
                user.save()
                
            self.stdout.write(self.style.SUCCESS(f"Processed {users.count()} users."))

