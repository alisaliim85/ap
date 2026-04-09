from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .utils import generate_empty_template, process_bulk_upload
import datetime
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from .forms_upload import MemberUploadForm
from accounts.models import User

class MemberDownloadTemplateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        stream = generate_empty_template()
        response = HttpResponse(
            content=stream.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"members_upload_template_{timestamp}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class MemberBulkUploadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'members/bulk_upload.html'
    permission_required = 'members.add_member' # إضافة حماية الصلاحيات (مهم جداً)

    def get(self, request, *args, **kwargs):
        # نمرر المستخدم للـ Form لكي يفلتر قائمة العملاء (Dropdown)
        form = MemberUploadForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        # نمرر المستخدم أيضاً عند استقبال البيانات
        form = MemberUploadForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            # العميل الآن يتم استخراجه بأمان من الـ Form نفسه بعد الفلترة والتحقق
            client = form.cleaned_data.get('client')
            file = form.cleaned_data.get('file')

            if not client:
                messages.error(request, "حدث خطأ: لم يتم تحديد الشركة المراد رفع البيانات لها.")
                return render(request, self.template_name, {'form': form})
            
            # معالجة الملف
            results = process_bulk_upload(file, client)
            
            # إعادة عرض الصفحة مع النتائج
            return render(request, self.template_name, {
                'form': MemberUploadForm(user=request.user), # فورم جديد لعملية رفع أخرى
                'results': results,
                'client': client
            })
            
        return render(request, self.template_name, {'form': form})