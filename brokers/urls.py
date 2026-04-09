from django.urls import path

# اسم التطبيق (مهم جداً لتنظيم المسارات لاحقاً)
app_name = 'brokers'

# القائمة التي يبحث عنها دجانغو (حتى لو كانت فارغة حالياً)
urlpatterns = [
    # سنقوم بإضافة المسارات الخاصة بلوحة تحكم الوسطاء هنا لاحقاً
    # path('', views.broker_dashboard, name='dashboard'),
]