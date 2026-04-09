from django import forms
from .models import Policy, PolicyClass, ClassBenefit, BenefitType
from clients.models import Client
from accounts.models import User

class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['client', 'master_policy', 'provider', 'policy_number', 'start_date', 'end_date', 'contract_file', 'is_active']
        widgets = {
            'client': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'master_policy': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
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

        # 2. تطبيق العزل على القوائم المنسدلة بناءً على الصلاحيات
        if self.user:
            if self.user.role == User.Roles.SUPER_ADMIN:
                # السوبر أدمن يرى جميع العملاء وجميع الوثائق الأم
                self.fields['client'].queryset = Client.objects.all()
                self.fields['master_policy'].queryset = Policy.objects.filter(master_policy__isnull=True)
                
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
            else:
                # إفراغ القوائم لأي مستخدم غير مصرح له كإجراء أمني
                self.fields['client'].queryset = Client.objects.none()
                self.fields['master_policy'].queryset = Policy.objects.none()
    
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