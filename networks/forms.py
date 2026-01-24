from django import forms
from .models import ServiceProvider, Network

class ServiceProviderForm(forms.ModelForm):
    class Meta:
        model = ServiceProvider
        fields = ['name_ar', 'name_en', 'type', 'city', 'address', 'latitude', 'longitude']
        widgets = {
            'name_ar': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'اسم المستشفى/المركز (عربي)'}),
            'name_en': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'Name (English)'}),
            'type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'city': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'المدينة'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'rows': 2, 'placeholder': 'العنوان التفصيلي'}),
            'latitude': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'Latitude'}),
            'longitude': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'Longitude'}),
        }

class NetworkForm(forms.ModelForm):
    class Meta:
        model = Network
        fields = ['provider', 'name_ar', 'name_en']
        widgets = {
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'}),
            'name_ar': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'اسم الشبكة (عربي)'}),
            'name_en': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500', 'placeholder': 'Network Name (English)'}),
        }
