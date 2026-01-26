from django import forms
from .models import Policy, PolicyClass, ClassBenefit, BenefitType

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
        super().__init__(*args, **kwargs)
        # Provider is optional in form because it might be inherited from master_policy
        self.fields['provider'].required = False
        self.fields['master_policy'].queryset = Policy.objects.filter(master_policy__isnull=True)
        self.fields['master_policy'].label = "الوثيقة الأم (للشركات القابضة)"
    
    def clean(self):
        cleaned_data = super().clean()
        master_policy = cleaned_data.get('master_policy')
        provider = cleaned_data.get('provider')
        
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
