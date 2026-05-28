"""
Management command: setup_roles
================================
ينشئ أو يحدّث مجموعات Django (Groups) بحيث تحمل كل مجموعة
الصلاحيات المناسبة لدورها في المنصة.

يجب تشغيل هذا الأمر:
    - بعد أي migrate جديد
    - عند إضافة صلاحيات جديدة للنماذج

الاستخدام:
    python manage.py setup_roles
    python manage.py setup_roles --reset   (يحذف الصلاحيات القديمة أولاً)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


# ============================================================
# تعريف الصلاحيات لكل دور
# الصيغة: 'app_label.codename'
# ============================================================
ROLE_PERMISSIONS = {

    # -------------------------------------------------------
    # BROKER_ADMIN — المدير الكامل للوسيط
    # يملك كامل الصلاحيات على بيانات الوسيط والعملاء والأعضاء
    # -------------------------------------------------------
    'BROKER_ADMIN': [
        # لوحة التحكم والمستخدمين
        'accounts.view_broker_dashboard',
        'accounts.manage_broker_staff',
        # العملاء (الشركات)
        'clients.view_client',
        'clients.add_client',
        'clients.change_client',
        'clients.manage_clients',
        'clients.view_client_dashboard',
        # الوثائق التأمينية
        'policies.view_policy',
        'policies.add_policy',
        'policies.change_policy',
        'policies.delete_policy',
        'policies.manage_insurance_plans',
        'policies.manage_benefit_types',
        'policies.manage_policy_structure',
        'policies.view_policy_details',
        # مزودو الخدمة الطبية (مستشفيات / عيادات)
        'networks.view_serviceprovider',
        'networks.add_serviceprovider',
        'networks.change_serviceprovider',
        'networks.delete_serviceprovider',
        'networks.manage_providers',
        'networks.bulk_upload_providers',
        # الشبكات الطبية
        'networks.view_network',
        'networks.add_network',
        'networks.change_network',
        'networks.delete_network',
        'networks.manage_networks',
        # الأعضاء
        'members.view_member',
        'members.add_member',
        'members.change_member',
        'members.delete_member',
        'members.view_all_members',
        'members.manage_members',
        'members.bulk_upload_members',
        # المطالبات
        'claims.can_submit_claim',
        'claims.can_process_broker',
        'claims.can_approve_payment',
        'claims.can_view_all_claims',
        'claims.view_sensitive_medical_data',
        # طلبات الخدمة
        'service_requests.can_submit_service_request',
        'service_requests.can_process_service_request',
        # الأدوية والصيدليات
        'medications.can_transfer_to_medications',
        'medications.can_view_medication_dashboard',
        'medications.can_schedule_refill',
        'medications.can_approve_refill',
        'medications.can_view_refill_alerts',
        # الشركاء (صيدليات / عيادات / مختبرات)
        'partners.view_partner',
        'partners.add_partner',
        'partners.change_partner',
        'partners.delete_partner',
        'partners.manage_partners',
        'partners.view_partner_contracts',
        # شركات التأمين
        'providers.view_provider',
        'providers.add_provider',
        'providers.change_provider',
        'providers.delete_provider',
        'providers.manage_insurance_companies',
        # الرعاية المزمنة
        'chronic_care.manage_disease_list',
        'chronic_care.manage_chronic_requests',
        'chronic_care.approve_request',
        'chronic_care.assign_partner',
        'chronic_care.manage_chronic_cases',
        'chronic_care.suspend_case',
        'chronic_care.manage_home_visits',
        'chronic_care.process_visit',
        'chronic_care.view_sensitive_medical_data',
        'chronic_care.upload_lab_result',
    ],

    # -------------------------------------------------------
    # BROKER_STAFF — موظف الوسيط
    # يعالج الطلبات والمطالبات دون صلاحيات الحذف أو إدارة الإعدادات
    # -------------------------------------------------------
    'BROKER_STAFF': [
        # لوحة التحكم
        'accounts.view_broker_dashboard',
        # العملاء (عرض فقط)
        'clients.view_client',
        'clients.view_client_dashboard',
        # الوثائق (عرض + إدارة الخطط)
        'policies.view_policy',
        'policies.view_policy_details',
        'policies.manage_insurance_plans',
        # مزودو الخدمة (عرض فقط)
        'networks.view_serviceprovider',
        'networks.view_network',
        # الأعضاء (عرض فقط)
        'members.view_member',
        'members.view_all_members',
        # المطالبات (معالجة وعرض)
        'claims.can_process_broker',
        'claims.can_view_all_claims',
        'claims.view_sensitive_medical_data',
        # طلبات الخدمة (معالجة)
        'service_requests.can_process_service_request',
        # الأدوية
        'medications.can_transfer_to_medications',
        'medications.can_view_medication_dashboard',
        'medications.can_schedule_refill',
        'medications.can_approve_refill',
        'medications.can_view_refill_alerts',
        # الشركاء (عرض فقط)
        'partners.view_partner',
        # شركات التأمين (عرض فقط)
        'providers.view_provider',
        # الرعاية المزمنة
        'chronic_care.manage_chronic_requests',
        'chronic_care.approve_request',
        'chronic_care.assign_partner',
        'chronic_care.manage_chronic_cases',
        'chronic_care.manage_home_visits',
        'chronic_care.process_visit',
        'chronic_care.view_sensitive_medical_data',
    ],

    # -------------------------------------------------------
    # HR_ADMIN — مدير الموارد البشرية في الشركة العميلة
    # يدير أعضاء شركته ويراجع المطالبات وطلبات الخدمة
    # -------------------------------------------------------
    'HR_ADMIN': [
        # لوحة التحكم وإدارة الموظفين
        'accounts.view_hr_dashboard',
        'accounts.manage_company_staff',
        # الوثائق (عرض فقط — لشركته)
        'policies.view_policy',
        'policies.view_policy_details',
        # الأعضاء (إدارة كاملة لشركته)
        'members.view_member',
        'members.add_member',
        'members.change_member',
        'members.delete_member',
        'members.view_all_members',
        'members.manage_members',
        'members.bulk_upload_members',
        # المطالبات (إرسال ومراجعة HR)
        'claims.can_submit_claim',
        'claims.can_approve_hr',
        'claims.can_reject_hr',
        'claims.can_view_all_claims',
        # طلبات الخدمة (إرسال ومراجعة HR)
        'service_requests.can_submit_service_request',
        'service_requests.can_process_hr_request',
        # شركات التأمين (عرض فقط — للإشارة)
        'providers.view_provider',
    ],

    # -------------------------------------------------------
    # HR_STAFF — موظف الموارد البشرية
    # يُدخل البيانات ويراجع الطلبات دون حذف أو إعدادات
    # -------------------------------------------------------
    'HR_STAFF': [
        # لوحة التحكم
        'accounts.view_hr_dashboard',
        # الوثائق (عرض فقط)
        'policies.view_policy',
        'policies.view_policy_details',
        # الأعضاء (عرض فقط)
        'members.view_member',
        'members.view_all_members',
        # المطالبات (إرسال ومراجعة HR)
        'claims.can_submit_claim',
        'claims.can_approve_hr',
        'claims.can_reject_hr',
        # طلبات الخدمة
        'service_requests.can_submit_service_request',
        'service_requests.can_process_hr_request',
    ],

    # -------------------------------------------------------
    # PHARMACIST — الصيدلاني في صيدلية شريكة
    # يصرف الأدوية ويرى لوحة التحكم الخاصة بالأدوية
    # -------------------------------------------------------
    'PHARMACIST': [
        'accounts.view_partner_dashboard',
        'medications.can_dispense_medication',
        'medications.can_view_medication_dashboard',
        'medications.can_view_refill_alerts',
    ],

    # -------------------------------------------------------
    # CHRONIC_ADMIN — مدير برنامج الرعاية المزمنة لدى الشريك
    # -------------------------------------------------------
    'CHRONIC_ADMIN': [
        'accounts.view_partner_dashboard',
        'chronic_care.manage_disease_list',
        'chronic_care.manage_chronic_requests',
        'chronic_care.approve_request',
        'chronic_care.assign_partner',
        'chronic_care.manage_chronic_cases',
        'chronic_care.suspend_case',
        'chronic_care.manage_home_visits',
        'chronic_care.process_visit',
        'chronic_care.view_sensitive_medical_data',
        'chronic_care.upload_lab_result',
        'medications.can_view_medication_dashboard',
    ],

    # -------------------------------------------------------
    # CHRONIC_STAFF — موظف برنامج الرعاية المزمنة لدى الشريك
    # -------------------------------------------------------
    'CHRONIC_STAFF': [
        'accounts.view_partner_dashboard',
        'chronic_care.manage_chronic_requests',
        'chronic_care.manage_chronic_cases',
        'chronic_care.manage_home_visits',
        'chronic_care.process_visit',
        'chronic_care.upload_lab_result',
    ],

    # -------------------------------------------------------
    # INSURANCE — مندوب شركة التأمين
    # يراجع المطالبات الواردة ويبتّ فيها من جانب التأمين
    # -------------------------------------------------------
    'INSURANCE': [
        'claims.can_process_insurance',
        'claims.can_view_all_claims',
        'claims.view_sensitive_medical_data',
    ],

    # -------------------------------------------------------
    # VIEWER — مراقب للقراءة فقط
    # يرى كل شيء دون أي صلاحية تعديل أو إجراء
    # -------------------------------------------------------
    'VIEWER': [
        'accounts.view_broker_dashboard',
        'clients.view_client',
        'clients.view_client_dashboard',
        'policies.view_policy',
        'policies.view_policy_details',
        'networks.view_serviceprovider',
        'networks.view_network',
        'members.view_member',
        'members.view_all_members',
        'claims.can_view_all_claims',
        'partners.view_partner',
        'providers.view_provider',
    ],

    # -------------------------------------------------------
    # MEMBER — المؤمن عليه / العضو
    # يرى وثيقته وعائلته ويرسل مطالباته وطلباته
    # -------------------------------------------------------
    'MEMBER': [
        'accounts.view_member_dashboard',
        'members.view_my_family_members',
        'claims.can_submit_claim',
        'service_requests.can_submit_service_request',
    ],
}


class Command(BaseCommand):
    help = (
        "Creates/updates Django Groups with the correct permissions for each role. "
        "Run after every migrate that adds new permissions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear all existing permissions from role groups before setting new ones.',
        )

    def handle(self, *args, **options):
        reset = options['reset']
        self.stdout.write(self.style.MIGRATE_HEADING("Setting up role groups and permissions…\n"))

        total_set = 0
        total_missing = 0

        for group_name, perm_codes in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            label = "Created" if created else "Updated"

            if reset:
                group.permissions.clear()

            perms_to_set = []
            missing = []

            for perm_code in perm_codes:
                try:
                    app_label, codename = perm_code.split('.', 1)
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"    Invalid permission format: {perm_code}"))
                    continue

                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    perms_to_set.append(perm)
                except Permission.DoesNotExist:
                    missing.append(perm_code)

            group.permissions.set(perms_to_set)
            total_set += len(perms_to_set)
            total_missing += len(missing)

            self.stdout.write(
                self.style.SUCCESS(f"  ✓ [{label}] {group_name:20s} — {len(perms_to_set)} permissions assigned")
            )
            for m in missing:
                self.stdout.write(self.style.WARNING(f"      ⚠  Not found (run migrate first?): {m}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done. {total_set} permissions assigned across {len(ROLE_PERMISSIONS)} groups."))
        if total_missing:
            self.stdout.write(self.style.WARNING(f"      {total_missing} permissions not found — run 'migrate' then retry."))
