from django import forms
from .models import Claim, ClaimComment
from members.models import Member

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)] if data else []
        return result

class ClaimCreateForm(forms.ModelForm):
    attachments = MultipleFileField(label='المرفقات', required=True)
    # Custom field for HR search
    national_id_search = forms.CharField(label='رقم الهوية للمستفيد', required=False, max_length=10)

    class Meta:
        model = Claim
        fields = ['member', 'service_date', 'currency', 'amount_original', 'is_in_patient', 'is_international']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ClaimCreateForm, self).__init__(*args, **kwargs)

        if self.user:
            # HR Logic
            if self.user.has_perm('accounts.view_hr_dashboard') or getattr(self.user, 'role', '') == 'HR':
                # HR doesn't use the standard member dropdown; they use national_id_search
                self.fields['member'].required = False
                self.fields['member'].widget = forms.HiddenInput()

            # Member Logic
            elif getattr(self.user, 'role', '') == 'MEMBER':
                self.fields['national_id_search'].widget = forms.HiddenInput()
                try:
                    member_profile = self.user.member_profile
                    # Filter: (id = self) OR (sponsor = self)
                    self.fields['member'].queryset = Member.objects.filter(
                        id=member_profile.id
                    ) | Member.objects.filter(sponsor=member_profile)
                except Exception:
                     self.fields['member'].queryset = Member.objects.none()
            else:
                 self.fields['member'].queryset = Member.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        
        # If HR, validate national_id_search and set member
        if self.user and (self.user.has_perm('accounts.view_hr_dashboard') or getattr(self.user, 'role', '') == 'HR'):
            national_id = cleaned_data.get('national_id_search')
            if not national_id:
                self.add_error('national_id_search', 'رقم الهوية مطلوب.')
            else:
                client = getattr(self.user, 'related_client', None)
                try:
                    member = Member.objects.get(national_id=national_id, client=client)
                    cleaned_data['member'] = member
                except Member.DoesNotExist:
                    self.add_error('national_id_search', 'لم يتم العثور على مستفيد برقم الهوية هذا في شركتك.')
        
        return cleaned_data

class ClaimCommentForm(forms.ModelForm):
    class Meta:
        model = ClaimComment
        fields = ['message', 'visibility']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition text-sm', 'placeholder': 'اكتب تعليقك هنا...'}),
            'visibility': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition text-sm'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # If user is MEMBER, they can only create GENERAL comments
            if getattr(self.user, 'role', '') == 'MEMBER':
                self.fields['visibility'].widget = forms.HiddenInput()
                self.fields['visibility'].initial = ClaimComment.Visibility.GENERAL
            # If user is HR, they can see GENERAL and HR_BROKER
            elif getattr(self.user, 'role', '') == 'HR' or self.user.has_perm('accounts.view_hr_dashboard'):
                self.fields['visibility'].choices = [
                    (ClaimComment.Visibility.GENERAL.value, ClaimComment.Visibility.GENERAL.label),
                    (ClaimComment.Visibility.HR_BROKER.value, ClaimComment.Visibility.HR_BROKER.label),
                ]
            # If user is Insurance, they can see GENERAL and BROKER_INSURANCE
            elif getattr(self.user, 'role', '') == 'INSURANCE': # Assuming INSURANCE role exists
                 self.fields['visibility'].choices = [
                    (ClaimComment.Visibility.GENERAL.value, ClaimComment.Visibility.GENERAL.label),
                    (ClaimComment.Visibility.BROKER_INSURANCE.value, ClaimComment.Visibility.BROKER_INSURANCE.label),
                ]
            # Broker and Superadmin see all choices (default)
