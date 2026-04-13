from django import forms
from clients.models import Client
from accounts.models import User

class MemberUploadForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=Client.objects.none(),
        label="الشركة (العميل)",
        required=True,
        widget=forms.Select(attrs={
            'class': 'block w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all shadow-sm text-sm'
        })
    )
    
    file = forms.FileField(
        label='ملف بيانات الأعضاء (Excel)',
        help_text='صيغة .xlsx فقط. يجب استخدام القالب المعتمد.',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100',
            'accept': '.xlsx'
        })
    )

    def __init__(self, *args, **kwargs):
        # استقبال المستخدم من الـ View
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # تطبيق العزل (Data Isolation) على قائمة العملاء
        if self.user:
            if self.user.role == User.Roles.SUPER_ADMIN:
                self.fields['client'].queryset = Client.objects.all()
                self.fields['client'].label_from_instance = lambda obj: f"{obj.name_en} - (الوسيط: {obj.broker.name_ar if obj.broker else 'بدون وسيط'})"
                
            elif self.user.is_broker_role and self.user.related_broker:
                self.fields['client'].queryset = Client.objects.filter(broker=self.user.related_broker)
                
            elif self.user.is_hr_role and self.user.related_client:
                # إذا كان HR، نحدد شركته فقط
                self.fields['client'].queryset = Client.objects.filter(id=self.user.related_client.id)
                self.fields['client'].initial = self.user.related_client
                # إخفاء الحقل عن الـ HR لتسهيل تجربة الاستخدام (UX)
                self.fields['client'].widget = forms.HiddenInput()

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and not file.name.endswith('.xlsx'):
            raise forms.ValidationError("يجب رفع ملف بصيغة Excel (.xlsx) فقط.")
        return file