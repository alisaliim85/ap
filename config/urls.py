from django.contrib import admin
from django.urls import path, include
from accounts.views import login_view # Keep login_view for the root path if desired

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # روابط الحسابات (شاملة تسجيل الدخول ولوحة التحكم وإدارة المستخدمين)
    path('', include('accounts.urls')),
    
    # روابط التطبيقات الأخرى
    path('clients/', include('clients.urls')),
    path('providers/', include('providers.urls')),
    path('partners/', include('partners.urls')),
    path('policies/', include('policies.urls')),
    path('networks/', include('networks.urls')),
]