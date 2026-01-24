from django import forms
from .models import Provider

class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['name_ar', 'name_en', 'license_number', 'claim_email', 'website', 'logo', 'is_active']
        widgets = {
            'name_ar': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'اسم شركة التأمين بالعربي'
            }),
            'name_en': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 
                'placeholder': 'Insurance Provider Name (EN)'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'رقم الترخيص'
            }),
            'claim_email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'claims@example.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500',
                'placeholder': 'https://example.com'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'
            }),
        }
