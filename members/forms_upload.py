from django import forms

class MemberUploadForm(forms.Form):
    file = forms.FileField(
        label='ملف بيانات الأعضاء (Excel)',
        help_text='صيغة .xlsx فقط. يجب استخدام القالب المعتمد.',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100',
            'accept': '.xlsx'
        })
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.xlsx'):
            raise forms.ValidationError("يجب رفع ملف بصيغة Excel (.xlsx) فقط.")
        return file
