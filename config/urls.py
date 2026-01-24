from django.contrib import admin
from django.urls import path, include
from accounts.views import login_view, logout_view, dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # روابط الحسابات
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # روابط تطبيق العملاء
    path('clients/', include('clients.urls')),
    
    # روابط تطبيق شركات التأمين
    path('providers/', include('providers.urls')),

    # روابط تطبيق الشركاء والمزودين
    path('partners/', include('partners.urls')),
]