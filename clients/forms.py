from django import forms
from .models import Client
from accounts.models import User

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        # تمت إضافة حقل broker ليكون متاحاً للسوبر أدمن
        fields = ['broker', 'name_ar', 'name_en', 'parent', 'commercial_record', 'email', 'phone', 'is_active']
        widgets = {
            'broker': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'name_ar': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'اسم الشركة بالعربي'
            }),
            'name_en': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 
                'placeholder': 'Company Name (EN)'
            }),
            'parent': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'commercial_record': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        # استخراج المستخدم المُمرر من الـ View
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # 1. فلترة حقل الشركة الأم (Parent) لكي لا يرى الوسيط شركات غيره
            parent_queryset = Client.objects.none()
            
            if self.user.role == User.Roles.SUPER_ADMIN:
                parent_queryset = Client.objects.all()
            elif self.user.is_broker_role and self.user.related_broker:
                parent_queryset = Client.objects.filter(broker=self.user.related_broker)
                
            # استبعاد الشركة نفسها من قائمة (Parent) لمنع التكرار الدائري أثناء التعديل
            if self.instance and self.instance.pk:
                parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
                
            self.fields['parent'].queryset = parent_queryset

            # 2. إخفاء حقل الوسيط (broker) عن مستخدمي الوسيط (لأنهم يضافون تلقائياً)
            if self.user.role != User.Roles.SUPER_ADMIN:
                if 'broker' in self.fields:
                    del self.fields['broker']