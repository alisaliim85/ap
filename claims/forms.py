from django import forms
from .models import Claim, ClaimComment
from members.models import Member
from accounts.models import User

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        # إضافة تنسيقات Tailwind لزر رفع الملفات
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'
        }))
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
    # تم توسيع استخدام هذا الحقل ليكون لـ (HR، الوسيط، والسوبر أدمن)
    national_id_search = forms.CharField(
        label='رقم الهوية للمستفيد (للبحث)', 
        required=False, 
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500'})
    )

    class Meta:
        model = Claim
        fields = ['member', 'service_date', 'currency', 'amount_original', 'is_in_patient', 'is_international']
        widgets = {
            'member': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md'}),
            'service_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-slate-300 rounded-md'}),
            'currency': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md'}),
            'amount_original': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-md'}),
            'is_in_patient': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'}),
            'is_international': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ClaimCreateForm, self).__init__(*args, **kwargs)

        if self.user:
            # 1. منطق العضو (Member)
            if self.user.is_member_role:
                # العضو لا يبحث برقم الهوية، بل يختار من قائمة عائلته المنسدلة
                self.fields['national_id_search'].widget = forms.HiddenInput()
                try:
                    member_profile = self.user.member_profile
                    # يرى نفسه ومكفوليه فقط
                    self.fields['member'].queryset = Member.objects.filter(
                        id=member_profile.id
                    ) | Member.objects.filter(sponsor=member_profile)
                except Exception:
                    self.fields['member'].queryset = Member.objects.none()
            
            # 2. منطق (السوبر أدمن، الوسيط، والـ HR)
            else:
                # لا نستخدم القائمة المنسدلة (dropdown) لأنها قد تحتوي على آلاف المشتركين وتسبب بطء
                # بل نعتمد على حقل البحث برقم الهوية `national_id_search`
                self.fields['member'].required = False
                self.fields['member'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        
        # إذا كان المستخدم ليس عضواً عادياً (يعني هو HR أو وسيط أو سوبر أدمن)
        if self.user and not self.user.is_member_role:
            national_id = cleaned_data.get('national_id_search')
            
            if not national_id:
                self.add_error('national_id_search', 'رقم الهوية مطلوب للبحث عن المستفيد.')
            else:
                try:
                    # تطبيق العزل (Data Isolation) عند البحث برقم الهوية
                    if self.user.role == User.Roles.SUPER_ADMIN:
                        # السوبر أدمن يمكنه إنشاء مطالبة لأي هوية في النظام
                        member = Member.objects.get(national_id=national_id)
                        
                    elif self.user.is_broker_role and self.user.related_broker:
                        # الوسيط يبحث فقط في هويات المشتركين التابعين لشركات وساطته
                        member = Member.objects.get(national_id=national_id, client__broker=self.user.related_broker)
                        
                    elif self.user.is_hr_role and self.user.related_client:
                        # الـ HR يبحث فقط في هويات موظفي شركته
                        member = Member.objects.get(national_id=national_id, client=self.user.related_client)
                        
                    else:
                        raise Member.DoesNotExist
                        
                    cleaned_data['member'] = member
                    
                except Member.DoesNotExist:
                    self.add_error('national_id_search', 'لم يتم العثور على مستفيد برقم الهوية هذا ضمن نطاق صلاحياتك.')
                except Member.MultipleObjectsReturned:
                    self.add_error('national_id_search', 'يوجد أكثر من مستفيد بنفس رقم الهوية (خطأ في البيانات).')
        
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
            # 1. العضو يكتب تعليقات عامة فقط
            if self.user.is_member_role:
                self.fields['visibility'].widget = forms.HiddenInput()
                self.fields['visibility'].initial = ClaimComment.Visibility.GENERAL
                
            # 2. الـ HR يكتب تعليقات عامة، أو داخلية للوسيط
            elif self.user.is_hr_role:
                self.fields['visibility'].choices = [
                    (ClaimComment.Visibility.GENERAL.value, ClaimComment.Visibility.GENERAL.label),
                    (ClaimComment.Visibility.HR_BROKER.value, ClaimComment.Visibility.HR_BROKER.label),
                ]
                
            # 3. شركة التأمين تكتب تعليقات عامة، أو داخلية للوسيط
            elif getattr(self.user, 'role', '') == User.Roles.INSURANCE: 
                 self.fields['visibility'].choices = [
                    (ClaimComment.Visibility.GENERAL.value, ClaimComment.Visibility.GENERAL.label),
                    (ClaimComment.Visibility.BROKER_INSURANCE.value, ClaimComment.Visibility.BROKER_INSURANCE.label),
                ]
            # الوسيط (Broker) والسوبر أدمن يحتفظون بجميع الخيارات الافتراضية