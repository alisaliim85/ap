from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from decimal import Decimal

from claims.models import Claim, Currency
from members.models import Member
from clients.models import Client
from providers.models import Provider
from networks.models import Network, ServiceProvider
from policies.models import Policy, PolicyClass
from accounts.models import User

class ClaimWorkflowTests(TestCase):
    def setUp(self):
        # 1. Create Users
        self.member_user = User.objects.create_user(username='member1', password='password', role=User.Roles.MEMBER, national_id='1000000001')
        self.hr_user = User.objects.create_user(username='hr1', password='password', role=User.Roles.HR_ADMIN, national_id='1000000002')
        self.broker_user = User.objects.create_user(username='broker1', password='password', role=User.Roles.BROKER_ADMIN, national_id='1000000003')

        # Grant permissions (simplification: assume roles have permissions or grant directly)
        # For simplicity in this test, I will force permissions or use users as arguments
        # Ideally, we should use permission groups, but for now I'll just rely on methods checking permissions if implemented
        # The transition methods use `permission=lambda i, u: u.has_perm(...)`
        # So I need to assign permissions to users.
        from django.contrib.auth.models import Permission

        can_submit = Permission.objects.get(codename='can_submit_claim')
        can_approve_hr = Permission.objects.get(codename='can_approve_hr')
        can_reject_hr = Permission.objects.get(codename='can_reject_hr')
        can_process_broker = Permission.objects.get(codename='can_process_broker')
        can_approve_payment = Permission.objects.get(codename='can_approve_payment')

        self.member_user.user_permissions.add(can_submit)
        self.hr_user.user_permissions.add(can_approve_hr, can_reject_hr)
        self.broker_user.user_permissions.add(can_process_broker, can_approve_payment)


        # 2. Create Currency
        self.currency = Currency.objects.create(code='SAR', name_ar='ريال سعودي', name_en='Saudi Riyal', exchange_rate=1.0)

        # 3. Create Provider (Insurance Company)
        self.provider = Provider.objects.create(
            name_ar='بوبا', name_en='Bupa', license_number='LIC-001'
        )

        # 4. Create Client
        self.client = Client.objects.create(
            name_ar='شركة الاختبار', name_en='Test Company', commercial_record='CR-001'
        )

        # 5. Create Network
        self.network = Network.objects.create(
            provider=self.provider, name_ar='شبكة 1', name_en='Network 1'
        )

        # 6. Create Policy
        self.policy = Policy.objects.create(
            client=self.client,
            provider=self.provider,
            policy_number='POL-001',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        # 7. Create Policy Class
        self.policy_class = PolicyClass.objects.create(
            policy=self.policy,
            network=self.network,
            name='Class A',
            annual_limit=100000
        )

        # 8. Create Member
        self.member = Member.objects.create(
            client=self.client,
            user=self.member_user,
            policy_class=self.policy_class,
            full_name='John Doe',
            national_id='1000000001',
            birth_date=date(1990, 1, 1),
            gender=Member.Gender.MALE,
            relation=Member.RelationType.PRINCIPAL,
            phone_number='0500000000'
        )

    def test_claim_creation_and_reference(self):
        """Test creating a claim and verifying reference number generation."""
        claim = Claim.objects.create(
            member=self.member,
            service_date=date.today(),
            currency=self.currency,
            amount_original=500.00
        )

        self.assertIsNotNone(claim.id)
        self.assertEqual(claim.status, Claim.Status.DRAFT)
        self.assertTrue(claim.claim_reference.startswith(f"CLM-{date.today().year}-"))
        # Verify format CLM-YYYY-XXXXX
        parts = claim.claim_reference.split('-')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], 'CLM')
        self.assertEqual(parts[1], str(date.today().year))
        self.assertEqual(len(parts[2]), 5)

    def test_claim_workflow_happy_path(self):
        """Test the happy path of a claim lifecycle."""
        claim = Claim.objects.create(
            member=self.member,
            service_date=date.today(),
            currency=self.currency,
            amount_original=1000.00
        )

        # 1. Submit to HR
        claim.submit_to_hr(self.member_user)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.SUBMITTED_TO_HR)

        # 2. HR Approve
        claim.hr_approve(self.hr_user)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.SUBMITTED_TO_BROKER)

        # 3. Broker Start Processing
        claim.broker_start_process(self.broker_user)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.BROKER_PROCESSING)

        # 4. Send to Insurance
        claim.sent_to_insurance(self.broker_user)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.SENT_TO_INSURANCE)

        # 5. Insurance Approve
        claim.insurance_approve(self.broker_user)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.APPROVED_BY_INSURANCE)

        # 6. Mark as Paid
        approved_amount = Decimal('900.00')
        claim.mark_as_paid(self.broker_user, approved_amount)
        claim.save()
        self.assertEqual(claim.status, Claim.Status.PAID)
        self.assertEqual(claim.approved_amount_sar, approved_amount)

    def test_hr_rejection(self):
        """Test HR rejection workflow."""
        claim = Claim.objects.create(
            member=self.member,
            service_date=date.today(),
            currency=self.currency,
            amount_original=200.00
        )

        # Submit to HR
        claim.submit_to_hr(self.member_user)
        claim.save()

        # HR Return
        reason = "Missing receipt"
        claim.hr_return(self.hr_user, reason)
        claim.save()

        self.assertEqual(claim.status, Claim.Status.RETURNED_BY_HR)
        self.assertEqual(claim.rejection_reason, reason)
