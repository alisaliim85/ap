from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .utils import generate_empty_template
import datetime
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from .forms_upload import MemberUploadForm
from .utils import process_bulk_upload

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



class MemberBulkUploadView(LoginRequiredMixin, View):
    template_name = 'members/bulk_upload.html'

    def get(self, request, *args, **kwargs):
        form = MemberUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = MemberUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Get Current Client (Similar logic to MemberForm)
            client = None
            if request.user.is_hr:
                client = request.user.related_client
            else:
                # If broker, we might need a way to specify client or context.
                # For now, let's assume HR context or infer from user.
                # Revisit if Broker is uploading (maybe select client in form?)
                # If broker, the form should probably have a client field.
                # But requirement mostly talks about "User HR".
                pass
            
            # If Client is not resolving (e.g. Superuser without client), handle error
            if not client and not request.user.is_superuser:
                 # TODO: Handle Broker picking client
                 pass

            # Assuming HR user for now as per "user HR can downlod" request
            if not client and request.user.is_superuser:
                 # Fallback for dev: maybe query param? or fail?
                 # Let's fail gracefully if no client logic yet for superuser
                 messages.error(request, "Superuser must act as client to upload (Not implemented yet).")
                 return redirect('members:member_list')
            
            file = form.cleaned_data['file']
            results = process_bulk_upload(file, client)
            
            # Render page with results
            return render(request, self.template_name, {
                'form': MemberUploadForm(), # New form for next upload
                'results': results,
                'client': client
            })
            
        return render(request, self.template_name, {'form': form})

