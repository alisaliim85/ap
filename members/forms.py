from django import forms
from .models import Member
from policies.models import PolicyClass
from clients.models import Client

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'client', 'policy_class', 'sponsor', 'full_name', 
            'national_id', 'medical_card_number', 'national_address', 'birth_date', 
            'gender', 'relation', 'phone_number', 'is_active'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500'}),
            'policy_class': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500'}),
            'sponsor': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500'}),
            'full_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'الاسم الكامل'}),
            'national_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'رقم الهوية / الإقامة'}),
            'medical_card_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'رقم البطاقة الطبية'}),
            'national_address': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'العنوان الوطني', 'rows': 3}),
            'birth_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500'}),
            'relation': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-brand-500 focus:border-brand-500', 'placeholder': '05xxxxxxxx'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-brand-600 border-slate-300 rounded focus:ring-brand-500'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        client_id = kwargs.pop('client_id', None)
        relation_type = kwargs.pop('relation_type', None)
        sponsor_id = kwargs.pop('sponsor_id', None)
        
        super().__init__(*args, **kwargs)

        # 0. رقم البطاقة الطبية غير إلزامي حالياً
        self.fields['medical_card_number'].required = False
        self.fields['medical_card_number'].widget.attrs.pop('required', None)

        # 1. صقل حقل العميل بناءً على الصلاحيات
        post_client_id = self.data.get('client') if self.is_bound else None
        
        target_client_id = None
        if user and user.is_hr:
            target_client_id = user.related_client.id
            self.fields['client'].initial = target_client_id
            self.fields['client'].widget = forms.HiddenInput()
        elif client_id or post_client_id:
            target_client_id = client_id or post_client_id
            if isinstance(target_client_id, list): 
                target_client_id = target_client_id[0]
            self.fields['client'].initial = target_client_id
            if client_id:
                self.fields['client'].widget = forms.HiddenInput()
        else:
            self.fields['client'].queryset = Client.objects.all()
            target_client_id = self.instance.client_id if self.instance.pk else None
            # إضافة HTMX لجلب الفئات عند اختيار الشركة (للوسيط)
            from django.urls import reverse_lazy
            self.fields['client'].widget.attrs.update({
                'hx-get': reverse_lazy('members:ajax_load_policy_classes'),
                'hx-target': '#id_policy_class',
                'hx-trigger': 'change',
                'hx-vals': 'js:{client_id: event.target.value}'
            })

        # 2. فلترة الفئات المتاحة
        if target_client_id:
            from django.db.models import Q
            try:
                # التحقق من أن القيمة ليست قائمة (في حال POST بجداول معينة)
                cid = target_client_id
                
                # الفئات المتاحة هي:
                # - الفئات المرتبطة ببوالص الشركة مباشرة
                # - أو الفئات المرتبطة بالبوليصة الأم (إذا كانت الشركة تابعة)
                query = Q(policy__client_id=cid)
                # إذا كانت ID تأكد من وجود الشركة
                try:
                    client_obj = Client.objects.get(id=cid)
                    if client_obj.parent_id:
                        query |= Q(policy__client_id=client_obj.parent_id, policy__master_policy__isnull=True)
                except Client.DoesNotExist:
                    pass
                
                # إظهار الفئات النشطة فقط 
                # (Active policies)
                self.fields['policy_class'].queryset = PolicyClass.objects.filter(query).distinct()
                
                # فلترة الكفلاء (الموظفين في نفس الشركة)
                self.fields['sponsor'].queryset = Member.objects.filter(
                    client_id=cid,
                    relation='PRINCIPAL'
                )
            except (ValueError, TypeError):
                self.fields['policy_class'].queryset = PolicyClass.objects.none()
                self.fields['sponsor'].queryset = Member.objects.none()
        else:
            self.fields['policy_class'].queryset = PolicyClass.objects.none()
            self.fields['sponsor'].queryset = Member.objects.none()

        # 3. إعدادات خاصة بالتابعين
        # نعتبره تابعاً إذا كان نوع العلاقة ليس موظفاً، أو إذا كان الزر مضغوطاً من صفحة موظف
        is_dependent = (relation_type and relation_type != 'PRINCIPAL') or (self.instance.pk and self.instance.relation != 'PRINCIPAL')
        
        # إذا كانت POST، قد تكون القيمة في الـ data
        if self.is_bound and not is_dependent:
             rel = self.data.get('relation')
             if rel and rel != 'PRINCIPAL':
                 is_dependent = True

        if relation_type:
            self.fields['relation'].initial = relation_type
        
        # إذا كان ثمة كفيل محدد (عند الضغط على إضافة تابع من صفحة الموظف)
        actual_sponsor_id = sponsor_id or (self.instance.sponsor_id if self.instance.pk else None)
        if actual_sponsor_id:
            try:
                sponsor = Member.objects.filter(id=actual_sponsor_id).first()
                if sponsor:
                    self.fields['sponsor'].initial = sponsor
                    self.fields['policy_class'].initial = sponsor.policy_class
                    
                    # توارث رقم الجوال إذا كان فرعياً ولم يتم إدخال رقم بعد
                    if not self.instance.pk:
                        self.fields['phone_number'].initial = sponsor.phone_number
            except (ValueError, TypeError):
                pass

        if is_dependent:
            self.fields['sponsor'].disabled = True
            self.fields['policy_class'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        
        relation = cleaned_data.get('relation')
        sponsor = cleaned_data.get('sponsor')
        policy_class = cleaned_data.get('policy_class')
        client = cleaned_data.get('client')

        # استعادة القيم للحقول المخفية أو المعطلة
        if not client:
            client = self.fields['client'].initial or self.instance.client
            cleaned_data['client'] = client

        if relation != 'PRINCIPAL':
            if not sponsor:
                sponsor = self.fields['sponsor'].initial or self.instance.sponsor
                cleaned_data['sponsor'] = sponsor
            
            if not policy_class:
                # محاولة جلب الفئة من الكفيل أولاً
                if sponsor:
                    cleaned_data['policy_class'] = sponsor.policy_class
                else:
                    cleaned_data['policy_class'] = self.fields['policy_class'].initial or self.instance.policy_class

        if relation != 'PRINCIPAL' and not cleaned_data.get('sponsor'):
            self.add_error('sponsor', "يجب تحديد الموظف (الكفيل) لهذا التابع.")
        
        if relation == 'PRINCIPAL' and cleaned_data.get('sponsor'):
            self.add_error('sponsor', "الموظف الأساسي لا يمكن أن يكون له كفيل.")
            
        return cleaned_data
