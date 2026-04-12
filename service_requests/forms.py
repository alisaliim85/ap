from django import forms
from .models import ServiceRequest
from members.models import Member
from accounts.models import User


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 '
                     'file:rounded-md file:border-0 file:text-sm file:font-semibold '
                     'file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)] if data else []
        return result


class ServiceRequestCreateForm(forms.Form):
    """
    نموذج إنشاء طلب — لا يرتبط مباشرة بموديل لأن الحقول الديناميكية تُدار بشكل مستقل.
    """
    request_type = forms.IntegerField(widget=forms.HiddenInput())

    # المستفيد — العضو يراه كقائمة منسدلة، والـ HR يبحث برقم الهوية
    member = forms.ModelChoiceField(
        queryset=Member.objects.none(),
        label='المستفيد',
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-md '
                     'focus:outline-none focus:ring-1 focus:ring-brand-500'
        }),
    )

    national_id_search = forms.CharField(
        label='رقم الهوية للمستفيد (للبحث)',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-slate-300 rounded-md '
                     'focus:outline-none focus:ring-1 focus:ring-brand-500'
        }),
    )

    attachments = MultipleFileField(label='المرفقات', required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # 1. العضو يرى نفسه ومكفوليه
            if self.user.is_member_role:
                self.fields['national_id_search'].widget = forms.HiddenInput()
                try:
                    member_profile = self.user.member_profile
                    self.fields['member'].queryset = (
                        Member.objects.filter(id=member_profile.id)
                        | Member.objects.filter(sponsor=member_profile)
                    )
                except Exception:
                    self.fields['member'].queryset = Member.objects.none()

            # 2. HR / Broker / Super Admin — بحث برقم الهوية
            else:
                self.fields['member'].required = False
                self.fields['member'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        # إذا كان المستخدم ليس عضواً عادياً (HR أو وسيط أو سوبر أدمن)
        if self.user and not self.user.is_member_role:
            national_id = cleaned_data.get('national_id_search')

            if not national_id:
                self.add_error('national_id_search', 'رقم الهوية مطلوب للبحث عن المستفيد.')
            else:
                try:
                    if self.user.role == User.Roles.SUPER_ADMIN:
                        member = Member.objects.get(national_id=national_id)
                    elif self.user.is_broker_role and self.user.related_broker:
                        member = Member.objects.get(
                            national_id=national_id,
                            client__broker=self.user.related_broker
                        )
                    elif self.user.is_hr_role and self.user.related_client:
                        member = Member.objects.get(
                            national_id=national_id,
                            client=self.user.related_client
                        )
                    else:
                        raise Member.DoesNotExist

                    cleaned_data['member'] = member
                except Member.DoesNotExist:
                    self.add_error(
                        'national_id_search',
                        'لم يتم العثور على مستفيد برقم الهوية هذا ضمن نطاق صلاحياتك.'
                    )
                except Member.MultipleObjectsReturned:
                    self.add_error(
                        'national_id_search',
                        'يوجد أكثر من مستفيد بنفس رقم الهوية (خطأ في البيانات).'
                    )

        return cleaned_data


def validate_dynamic_data(fields_schema, post_data):
    """
    التحقق من صحة البيانات الديناميكية بناءً على مخطط الحقول.
    Returns: (cleaned_data: dict, errors: dict)
    """
    cleaned = {}
    errors = {}

    for field in fields_schema:
        name = field.get('name', '')
        label = field.get('label', name)
        field_type = field.get('type', 'text')
        required = field.get('required', False)

        value = post_data.get(f'dynamic_{name}', '').strip()

        # checkbox تتعامل بطريقة مختلفة
        if field_type == 'checkbox':
            value = f'dynamic_{name}' in post_data
            cleaned[name] = value
            continue

        # التحقق من الحقول المطلوبة
        if required and not value:
            errors[name] = f'حقل "{label}" مطلوب.'
            continue

        if value:
            # التحقق من الأنواع
            if field_type == 'number':
                try:
                    value = float(value)
                except ValueError:
                    errors[name] = f'حقل "{label}" يجب أن يكون رقماً.'
                    continue

            if field_type == 'select':
                choices = field.get('choices', [])
                valid_values = [c.get('value', '') for c in choices]
                if value not in valid_values:
                    errors[name] = f'القيمة المختارة في حقل "{label}" غير صالحة.'
                    continue

        cleaned[name] = value

    return cleaned, errors
