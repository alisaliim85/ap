from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServiceRequestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'service_requests'
    verbose_name = _("Service Requests")
