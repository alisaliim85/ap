from django import forms
from .models import Policy, PolicyClass, ClassBenefit, BenefitType, InsurancePlan, PlanClass, PlanClassBenefit
from clients.models import Client, SponsorNumber
from accounts.models import User

class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['client', 'sponsor_number', 'master_policy', 'provider', 'plan', 'policy_number', 'start_date', 'end_date', 'contract_file', 'is_active']
        widgets = {
            'client': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'sponsor_number': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'master_policy': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'plan': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
            }),
            'policy_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'رقم البوليصة'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'type': 'date'}),
            'contract_file': forms.FileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'}),
        }

    def __init__(self, *args, **kwargs):
        # 1. استخراج المستخدم المُمرر من الـ View
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # حقل مزود التأمين اختياري لأنه قد يورث من الوثيقة الأم
        self.fields['provider'].required = False
        self.fields['master_policy'].label = "الوثيقة الأم (للشركات القابضة)"
        self.fields['plan'].required = False
        self.fields['plan'].label = "خطة التأمين (اختياري — يُولِّد الفئات تلقائياً)"
        self.fields['sponsor_number'].required = False
        self.fields['sponsor_number'].label = "رقم الكفيل (اختياري — للكفلاء)"

        # 2. تطبيق العزل على القوائم المنسدلة بناءً على الصلاحيات
        if self.user:
            if self.user.role == User.Roles.SUPER_ADMIN:
                # السوبر أدمن يرى جميع العملاء وجميع الوثائق الأم
                self.fields['client'].queryset = Client.objects.all()
                self.fields['master_policy'].queryset = Policy.objects.filter(master_policy__isnull=True)
                self.fields['plan'].queryset = InsurancePlan.objects.select_related('provider').all()

                # تحسين تجربة السوبر أدمن: إظهار اسم الوسيط بجانب اسم العميل في القائمة
                self.fields['client'].label_from_instance = lambda obj: f"{obj.name_en} - (الوسيط: {obj.broker.name_ar if obj.broker else 'بدون وسيط'})"
                
            elif self.user.is_broker_role and self.user.related_broker:
                # الوسيط يرى عملاءه فقط
                self.fields['client'].queryset = Client.objects.filter(broker=self.user.related_broker)
                
                # الوسيط يرى فقط الوثائق الأم التي تعود لشركات تابعة له
                self.fields['master_policy'].queryset = Policy.objects.filter(
                    master_policy__isnull=True, 
                    client__broker=self.user.related_broker
                )
                # الوسيط يرى خططه فقط
                self.fields['plan'].queryset = InsurancePlan.objects.filter(
                    broker=self.user.related_broker,
                    is_active=True,
                ).select_related('provider')
            else:
                # إفراغ القوائم لأي مستخدم غير مصرح له كإجراء أمني
                self.fields['client'].queryset = Client.objects.none()
                self.fields['master_policy'].queryset = Policy.objects.none()
                self.fields['plan'].queryset = InsurancePlan.objects.none()

        # فلترة أرقام الكفيلة حسب العميل المحدد (كل أرقام مجموعة القابضة)
        selected_client = None
        if self.is_bound and self.data.get('client'):
            selected_client = Client.objects.filter(id=self.data.get('client')).first()
        elif self.instance.pk and self.instance.client_id:
            selected_client = self.instance.client

        from clients.models import get_group_root
        if selected_client:
            group_root = get_group_root(selected_client)
            self.fields['sponsor_number'].queryset = SponsorNumber.objects.filter(
                group=group_root,
                is_active=True,
            ).select_related('owner_client')
            self.fields['sponsor_number'].label_from_instance = (
                lambda obj: f"{obj.sponsor_number} - {obj.owner_client.name_en}"
            )
        else:
            # قبل اختيار العميل: نعرض كفلاء كل العملاء المسموحين
            allowed_clients = self.fields['client'].queryset
            if allowed_clients:
                group_ids = set()
                for c in allowed_clients:
                    group_ids.add(get_group_root(c).pk)
                self.fields['sponsor_number'].queryset = SponsorNumber.objects.filter(
                    group_id__in=group_ids,
                    is_active=True,
                ).select_related('owner_client')
                self.fields['sponsor_number'].label_from_instance = (
                    lambda obj: f"{obj.sponsor_number} - {obj.owner_client.name_en}"
                )

        # HTMX: جلب أرقام الكفيلة تلقائياً عند تغيير العميل
        from django.urls import reverse_lazy
        self.fields['client'].widget.attrs.update({
            'hx-get': reverse_lazy('policies:ajax_load_sponsor_numbers'),
            'hx-target': '#id_sponsor_number',
            'hx-trigger': 'change',
            'hx-vals': 'js:{client_id: this.value}',
        })
    
    def clean(self):
        cleaned_data = super().clean()
        master_policy = cleaned_data.get('master_policy')
        provider = cleaned_data.get('provider')
        
        # التحقق من وجود وثيقة أم أو مزود تأمين
        if not master_policy and not provider:
            raise forms.ValidationError("يجب تحديد إما الوثيقة الأم أو شركة التأمين المزودة.")
        
        return cleaned_data


class PolicyClassForm(forms.ModelForm):
    class Meta:
        model = PolicyClass
        fields = ['name', 'network', 'annual_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'اسم الفئة (مثلاً: VIP)'}),
            'network': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'annual_limit': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
        }


class ClassBenefitForm(forms.ModelForm):
    class Meta:
        model = ClassBenefit
        fields = ['benefit_type', 'limit_amount', 'deductible_percentage', 'description']
        widgets = {
            'benefit_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'limit_amount': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'deductible_percentage': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'rows': 2}),
        }


FIELD_CSS = 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'


class InsurancePlanForm(forms.ModelForm):
    """نموذج إنشاء/تعديل خطة تأمين."""

    class Meta:
        model = InsurancePlan
        fields = ['provider', 'name', 'description', 'is_active']
        widgets = {
            'provider': forms.Select(attrs={'class': FIELD_CSS}),
            'name': forms.TextInput(attrs={'class': FIELD_CSS, 'placeholder': 'مثال: بوبا الذهبي 2026'}),
            'description': forms.Textarea(attrs={'class': FIELD_CSS, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # فلترة شركات التأمين المتاحة (عالمية — لا عزل على Provider)
        from providers.models import Provider
        self.fields['provider'].queryset = Provider.objects.all().order_by('name_en')


class PlanClassForm(forms.ModelForm):
    """نموذج إضافة/تعديل فئة داخل خطة التأمين."""

    class Meta:
        model = PlanClass
        fields = ['name', 'network', 'annual_limit', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': FIELD_CSS, 'placeholder': 'مثال: VIP، فئة أ'}),
            'network': forms.Select(attrs={'class': FIELD_CSS}),
            'annual_limit': forms.NumberInput(attrs={'class': FIELD_CSS, 'step': '0.01'}),
            'order': forms.NumberInput(attrs={'class': FIELD_CSS}),
        }

    def __init__(self, *args, **kwargs):
        self.plan = kwargs.pop('plan', None)
        super().__init__(*args, **kwargs)
        if self.plan and self.plan.provider_id:
            from networks.models import Network
            self.fields['network'].queryset = Network.objects.filter(
                provider=self.plan.provider
            ).order_by('name_ar')
        else:
            from networks.models import Network
            self.fields['network'].queryset = Network.objects.none()
        self.fields['network'].required = False


class PlanClassBenefitForm(forms.ModelForm):
    """نموذج إضافة/تعديل منفعة داخل فئة خطة التأمين."""

    class Meta:
        model = PlanClassBenefit
        fields = ['benefit_type', 'limit_amount', 'deductible_percentage', 'description']
        widgets = {
            'benefit_type': forms.Select(attrs={'class': FIELD_CSS}),
            'limit_amount': forms.NumberInput(attrs={'class': FIELD_CSS, 'step': '0.01'}),
            'deductible_percentage': forms.NumberInput(attrs={'class': FIELD_CSS}),
            'description': forms.Textarea(attrs={'class': FIELD_CSS, 'rows': 2}),
        }