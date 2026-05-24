from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User
from clients.models import Client
from brokers.models import Broker
from partners.models import Partner

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all',
        'placeholder': 'اسم المستخدم',
        'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all',
        'placeholder': 'كلمة المرور'
    }))

class StaffUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
            'placeholder': 'كلمة المرور'
        }),
        required=False,
        label="كلمة المرور"
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role',
            'related_broker', 'related_client', 'related_partner',
            'phone_number', 'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'اسم المستخدم (English)'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'الاسم الأول'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'اسم العائلة'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'example@domain.com'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'related_broker': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'related_client': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'related_partner': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': '05xxxxxxxx'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'related_broker' in self.fields:
            self.fields['related_broker'].required = False
            self.fields['related_broker'].empty_label = "— لا يتبع وسيطاً —"
        if 'related_client' in self.fields:
            self.fields['related_client'].required = False
            self.fields['related_client'].empty_label = "— لا يتبع شركة —"
        if 'related_partner' in self.fields:
            self.fields['related_partner'].required = False
            self.fields['related_partner'].empty_label = "— لا يتبع شريكاً —"

        if self.instance.pk:
            self.fields['password'].help_text = "اتركه فارغاً إذا كنت لا ترغب في تغيير كلمة المرور"
        else:
            self.fields['password'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class BrokerStaffForm(StaffUserForm):
    """
    نموذج لمدراء الوسيط — ينشئ BROKER_STAFF فقط.
    الدور والوسيط يُعيَّنان تلقائياً من المستخدم المنشئ.
    """
    class Meta(StaffUserForm.Meta):
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['role', 'related_broker', 'related_client', 'related_partner']:
            self.fields.pop(f, None)


class HRStaffForm(StaffUserForm):
    """
    نموذج مبسط لمدراء الموارد البشرية لإضافة موظفيهم
    """
    class Meta(StaffUserForm.Meta):
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إزالة الحقول التي لا يحق للـ HR التحكم بها
        if 'role' in self.fields: del self.fields['role']
        if 'related_client' in self.fields: del self.fields['related_client']

class ProfileForm(StaffUserForm):
    class Meta(StaffUserForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove fields that we don't want editable or even in the form
        if 'password' in self.fields: del self.fields['password']
        if 'role' in self.fields: del self.fields['role']
        if 'related_client' in self.fields: del self.fields['related_client']
        if 'is_active' in self.fields: del self.fields['is_active']
        if 'username' in self.fields: del self.fields['username']