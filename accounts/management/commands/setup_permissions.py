from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

class Command(BaseCommand):
    help = 'Setup system groups and assign permissions automatically'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting permission setup...'))

        # ==============================================================================
        # 1. تعريف مصفوفة الصلاحيات لكل دور وظيفي
        # ==============================================================================
        
        # --- أ. مدير الوسيط (Broker Admin) ---
        # يملك صلاحيات إدارة النظام بالكامل (ما عدا صلاحيات السوبر أدمن التقنية)
        broker_admin_perms = [
            # Accounts
            'view_broker_dashboard', 'manage_users',
            # Clients
            'manage_clients', 'view_client_dashboard',
            # Claims
            'can_process_broker', 'can_approve_payment', 'can_view_all_claims', 'view_sensitive_medical_data',
            # Members
            'view_all_members', 'manage_members', 'bulk_upload_members', 'view_sensitive_member_data',
            # Policies
            'manage_benefit_types', 'manage_policy_structure', 'view_policy_details',
            # Networks & Providers
            'manage_providers', 'bulk_upload_providers', 'manage_networks', # Hospitals
            'manage_insurance_companies', # Insurance Companies
            # Partners
            'manage_partners', 'view_partner_contracts',
            # Chronic Care
            'manage_disease_list', 'approve_request', 'assign_partner', 'suspend_case'
        ]

        # --- ب. موظف عمليات الوسيط (Broker Staff) ---
        # صلاحيات أقل (لا يحذف، لا يرى العقود، لا يعدل الهيكلة)
        broker_staff_perms = [
            'view_broker_dashboard',
            'view_client_dashboard',
            'can_process_broker', 'can_view_all_claims',
            'view_all_members',
            'view_policy_details',
            'view_providers', # Default Django view perm
            'view_networks',  # Default Django view perm
            'approve_request', 'assign_partner'
        ]

        # --- ج. مدير الموارد البشرية (HR Manager) ---
        hr_manager_perms = [
            'view_hr_dashboard',
            'can_submit_claim', 'can_approve_hr', 'can_reject_hr',
            'view_all_members', 'manage_members', 'bulk_upload_members',
            'view_client_dashboard',
            'view_policy_details'
        ]

        # --- د. الفريق الطبي (Medical Team) ---
        medical_team_perms = [
            'process_visit', 'view_sensitive_medical_data',
            'upload_lab_result',
            'view_sensitive_member_data' # لرؤية الملف الطبي
        ]

        # ==============================================================================
        # 2. قاموس التجميع
        # ==============================================================================
        groups_config = {
            'Broker Admin': broker_admin_perms,
            'Broker Operations': broker_staff_perms,
            'HR Manager': hr_manager_perms,
            'Medical Team': medical_team_perms,
        }

        # ==============================================================================
        # 3. التنفيذ
        # ==============================================================================
        for group_name, codenames in groups_config.items():
            # إنشاء المجموعة أو جلبها
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"Created group: {group_name}")
            else:
                self.stdout.write(f"Updating group: {group_name}")

            # تنظيف الصلاحيات القديمة لإعادة تعيينها نظيفة
            group.permissions.clear()

            # البحث عن الصلاحيات وإضافتها
            for codename in codenames:
                try:
                    # نستخدم Q للبحث عن الصلاحية بغض النظر عن التطبيق (لأن الأسماء فريدة)
                    perm = Permission.objects.get(codename=codename)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Warning: Permission '{codename}' not found! Check your models."))
                except Permission.MultipleObjectsReturned:
                    # في حال تكرار الاسم (نادراً مع تصميمنا)، نأخذ أول واحدة
                    perm = Permission.objects.filter(codename=codename).first()
                    group.permissions.add(perm)
                    self.stdout.write(self.style.NOTICE(f"Notice: Multiple perms found for '{codename}', took first one."))

            self.stdout.write(self.style.SUCCESS(f"Successfully updated permissions for: {group_name}"))

        self.stdout.write(self.style.SUCCESS('--------------------------------------'))
        self.stdout.write(self.style.SUCCESS('ALL DONE! System is ready.'))