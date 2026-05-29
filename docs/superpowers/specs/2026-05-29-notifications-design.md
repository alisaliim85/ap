# نظام الإشعارات الداخلية — وثيقة التصميم

**التاريخ:** 2026-05-29  
**النطاق:** طلبات الخدمة (`service_requests`) والمطالبات المالية (`claims`)  
**القرار المعماري:** تطبيق Django مستقل `notifications/`

---

## 1. الهدف والنطاق

بناء نظام إشعارات داخلي شامل يخدم تطبيقَي `service_requests` و`claims`، يشمل:

1. **إشعارات تلقائية** — تُرسَل عند كل تغيير حالة ذي صلة بالمستخدم المعني.
2. **بريد داخلي موجَّه** — رسائل ثنائية الاتجاه بين الوسيط/الإداري وأصحاب الطلبات، مع إمكانية ربطها بطلب أو مطالبة محددة.

**خارج النطاق:** البريد الإلكتروني، SMS، push notifications — يمكن إضافتها لاحقاً دون تغيير البنية الحالية.

---

## 2. القرارات التصميمية

| القرار | الاختيار | المبرر |
|---|---|---|
| قنوات التوصيل | داخل النظام فقط | لا بنية تحتية خارجية، أسرع تنفيذاً |
| التوجيه | حسب الحالة (context-aware) | تجنب إشعار fatigue، أفضل ممارسة مؤسسية |
| الرسائل | ثنائية الاتجاه + مرتبطة بالطلب + بريد عام | يقلل المكالمات الهاتفية، سجل موثّق |
| التحديث | HTMX polling كل 30 ثانية | بدون WebSocket — مناسب للحجم الحالي |
| الخلفية | Django Signals متزامنة | إشعار DB write لا يستوجب Celery |
| البنية | تطبيق `notifications/` مستقل | حدود واضحة، لا يلوّث Apps الأخرى |

---

## 3. نماذج البيانات

### 3.1 `Notification` — الإشعار التلقائي

```python
class Notification(models.Model):
    class Type(models.TextChoices):
        STATUS_CHANGE = 'STATUS_CHANGE', 'تغيير حالة'
        MESSAGE       = 'MESSAGE',       'رسالة جديدة'
        REPLY         = 'REPLY',         'رد جديد'

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                          related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=Type.choices)
    title             = models.CharField(max_length=200)
    body              = models.TextField(blank=True)
    url               = models.CharField(max_length=500, blank=True)
    is_read           = models.BooleanField(default=False, db_index=True)
    # Generic FK — يربط بأي نموذج (ServiceRequest, Claim, ...)
    content_type      = models.ForeignKey(ContentType, on_delete=models.SET_NULL,
                                          null=True, blank=True)
    object_id         = models.UUIDField(null=True, blank=True)
    content_object    = GenericForeignKey('content_type', 'object_id')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
```

**سبب الـ Generic FK:** يتيح لنظام الإشعارات العمل مع أي نموذج مستقبلاً (مثل `chronic_care`) بدون تعديل.

### 3.2 `Message` — البريد الداخلي

```python
class Message(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='sent_messages')
    recipient    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='received_messages')
    subject      = models.CharField(max_length=300)
    body         = models.TextField()
    # Thread: الرسائل الجذرية (parent=None)، الردود تشير للجذر مباشرة
    parent       = models.ForeignKey('self', on_delete=models.CASCADE,
                                     null=True, blank=True, related_name='replies')
    # المرفق على الرسائل الجذرية فقط (ليس على الردود)
    attachment   = models.FileField(upload_to='notifications/attachments/%Y/%m/',
                                    null=True, blank=True)
    is_read      = models.BooleanField(default=False, db_index=True)
    # ربط اختياري بطلب أو مطالبة
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL,
                                     null=True, blank=True)
    object_id    = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
```

**قاعدة الـ Thread:** `parent` يشير دائماً للرسالة الجذرية مباشرة (ليس للرد). هذا يجعل استعلام "أعطني كل ردود هذه المحادثة" استعلاماً واحداً بسيطاً.

---

## 4. آلية الإرسال التلقائي

### 4.1 التدفق

```
View / FSM Transition
        ↓
post_save Signal (notifications/signals.py)
        ↓
    يفحص: هل تغيّر حقل status فعلاً؟
        ↓ نعم
NotificationService.notify_status_change(instance, old_status, new_status)
        ↓
يحدد المستلمين حسب خريطة التوجيه
        ↓
Notification.objects.bulk_create([...])
```

**ملاحظة أداء:** يُقارَن `instance.status` مع القيمة المحفوظة في `pre_save` لاكتشاف التغيير فعلياً، بدلاً من الاعتماد على `update_fields`.

**تجنب N+1 في الـ Signal:** عند الحاجة لـ `instance.member.client`، يُعاد تحميل الـ instance بـ `select_related` مرة واحدة:

```python
instance = ServiceRequest.objects.select_related('member__client').get(pk=instance.pk)
```

هذا يضمن ضربة واحدة على قاعدة البيانات بدلاً من ثلاث.

### 4.2 خريطة التوجيه — طلبات الخدمة

| الحالة الجديدة | من يُبلَّغ | نص الإشعار |
|---|---|---|
| `SUBMITTED` | الـ HR المسؤول عن الشركة | "طلب خدمة جديد يحتاج مراجعتك — {reference}" |
| `IN_REVIEW` | العضو صاحب الطلب | "طلبك {reference} قيد المراجعة من قِبل الوسيط" |
| `RETURNED` | العضو صاحب الطلب | "طلبك {reference} أُعيد — يرجى مراجعة الملاحظات" |
| `RESOLVED` | العضو صاحب الطلب | "طلبك {reference} تم حله بنجاح ✅" |
| `REJECTED` | العضو صاحب الطلب | "طلبك {reference} تم رفضه" |

**حالات بدون إشعار:** `DRAFT`، `HR_REVIEW`، `TRANSFERRED_TO_MEDICATIONS` — هذه حالات داخلية لا يحتاج العضو إلى معرفتها فوراً.

### 4.3 خريطة التوجيه — المطالبات المالية

| الحالة الجديدة | من يُبلَّغ | نص الإشعار |
|---|---|---|
| `SUBMITTED_TO_HR` | الـ HR المسؤول عن الشركة | "مطالبة جديدة تحتاج مراجعتك — {reference}" |
| `RETURNED_BY_HR` | العضو صاحب المطالبة | "مطالبتك {reference} أُعيدت — ناقص مستندات" |
| `SUBMITTED_TO_BROKER` | العضو صاحب المطالبة | "مطالبتك {reference} أُحيلت للوسيط للمراجعة" |
| `RETURNED_BY_BROKER` | العضو + الـ HR | "مطالبتك {reference} أُعيدت من الوسيط — يحتاج إجراء" |
| `SENT_TO_INSURANCE` | العضو صاحب المطالبة | "مطالبتك {reference} أُرسلت لشركة التأمين" |
| `APPROVED_BY_INSURANCE` | العضو + الـ HR | "مطالبتك {reference} وافقت عليها شركة التأمين ✅" |
| `REJECTED_BY_INSURANCE` | العضو + الـ HR | "مطالبتك {reference} رُفضت من شركة التأمين" |
| `PAID` | العضو صاحب المطالبة | "تم صرف مستحقات مطالبتك {reference} 💰" |

### 4.4 تحديد الـ HR المسؤول

عند إرسال إشعار للـ HR، يُرسَل لـ **جميع** مستخدمي `HR_ADMIN` و`HR_STAFF` المرتبطين بنفس `client` صاحب الطلب:

```python
hr_users = User.objects.filter(
    role__in=['HR_ADMIN', 'HR_STAFF'],
    related_client=instance.member.client,
    is_active=True
)
```

---

## 5. واجهة المستخدم

### 5.1 مكونات الواجهة

| المكون | الملف | الوصف |
|---|---|---|
| جرس الإشعارات | `includes/sidebar.html` + `_bell_badge.html` | badge أحمر بالعدد غير المقروء، polling كل 30 ثانية |
| Toast بانر | `_toast.html` | يظهر 5 ثوانٍ عند وصول إشعار جديد، Alpine.js للإخفاء |
| صفحة الإشعارات | `list.html` | كل الإشعارات مع فلتر (الكل / غير مقروء) |
| صندوق الوارد | `messages_inbox.html` | قائمة المحادثات (split view) |
| عرض المحادثة | `message_thread.html` | الرسالة + ردودها + خانة الرد |

### 5.2 HTMX Polling للجرس

```html
<!-- في sidebar.html -->
<div id="notification-badge"
     hx-get="{% url 'notifications:unread-count' %}"
     hx-trigger="load, every 30s"
     hx-swap="outerHTML">
  {# يُحدَّث بـ _bell_badge.html #}
</div>
```

الـ endpoint يعيد **HTML مصغّراً فقط** (رقم أو فراغ) — لا JSON، لا serialization.

### 5.3 Toast عند وصول إشعار جديد

يُعرض Toast عبر HTMX OOB swap في نفس استجابة polling. آلية الاكتشاف: الـ view يقبل query param `?since=<timestamp>`، ويُرجع Toast إذا وُجد إشعار `created_at > since`. الـ JS helper يُرسل timestamp آخر فحص مع كل polling request.

---

## 6. URL Patterns

```python
# notifications/urls.py
app_name = 'notifications'

urlpatterns = [
    # إشعارات
    path('', views.NotificationListView.as_view(), name='list'),
    path('unread-count/', views.unread_count, name='unread-count'),
    path('mark-read/<uuid:pk>/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),

    # رسائل
    path('messages/', views.MessageInboxView.as_view(), name='inbox'),
    path('messages/<uuid:pk>/', views.MessageThreadView.as_view(), name='thread'),
    path('messages/compose/', views.ComposeMessageView.as_view(), name='compose'),
    path('messages/<uuid:pk>/reply/', views.ReplyMessageView.as_view(), name='reply'),
]
```

**صلاحيات:** `compose/` محمي — يتطلب دور `BROKER_ADMIN` أو `BROKER_STAFF` أو `SUPER_ADMIN`. `reply/` مفتوح لكلٍّ من `sender` و`recipient` للرسالة الجذرية — أي طرف في المحادثة يستطيع الرد.

**ملاحظة هيكلية مهمة:** الـ Thread في هذا النظام صارم بين **طرفين فقط** (sender و recipient للجذر). لا توجد آلية لإضافة طرف ثالث داخل thread موجود — أي مراسلة لشخص آخر تبدأ بـ root message جديدة. لذلك التحقق من الجذر وحده مكافئ للتحقق من Thread كامل.

**تحقق إضافي إلزامي في `reply/`:** يجب أن يكون الـ `pk` المُمرَّر رسالةً جذرية (`parent=None`) حصراً. إذا كان الـ pk لـ reply، يُرجع الـ view خطأ `400 Bad Request` لمنع إنشاء replies متداخلة تكسر بنية الـ Thread.

---

## 7. هيكل الملفات

```
notifications/
├── __init__.py
├── apps.py               ← يسجّل Signals في ready()
├── models.py             ← Notification + Message
├── signals.py            ← post_save للـ ServiceRequest و Claim
├── services.py           ← NotificationService (منطق التوجيه)
├── views.py              ← 8 views
├── urls.py
├── admin.py
└── migrations/

templates/notifications/
├── list.html             ← صفحة الإشعارات الكاملة
├── messages_inbox.html   ← صندوق الوارد (split view)
├── message_thread.html   ← عرض المحادثة + رد
├── _bell_badge.html      ← HTMX partial للجرس
├── _notification_item.html ← HTMX partial لعنصر واحد
└── _toast.html           ← HTMX partial للبانر
```

---

## 8. ضمانات الأداء

### 8.1 قاعدة البيانات
- فهرس مركّب `(recipient, is_read, created_at)` على كلا النموذجين
- استعلام العدد غير المقروء: `Notification.objects.filter(recipient=user, is_read=False).count()` — يستغرق < 1ms
- جداول منفصلة تماماً — **لا تعديل** على جداول `service_requests` أو `claims`

### 8.2 HTMX Polling — Adaptive (Smart)
- الأساس: طلب كل 30 ثانية — طلب HTTP عادي يعيد HTML مصغّر
- يُوقف تلقائياً عند `hx-trigger="every 30s [document.hidden !== true]"` (لا طلبات أثناء قفل الشاشة)
- **Exponential Backoff عبر Alpine.js:** إذا لم تكن هناك إشعارات جديدة لـ 3 دورات متتالية، ترتفع المدة من 30s إلى 60s تلقائياً. تعود إلى 30s فور أي حركة من المستخدم (mousemove / click). يُقلل هذا الضغط على الخادم بـ ~40% في أوقات الخمول.

### 8.3 Django Signals
- يُقارَن `status` قبل وبعد الحفظ عبر `pre_save` + `post_save` معاً
- لا يُنشئ إشعاراً إذا لم تتغير الحالة فعلاً
- إنشاء الإشعار داخل نفس الـ database transaction — إذا فشل الحفظ، لا إشعار مزيّف

---

## 9. نقاط التكامل مع النظام الحالي

| الملف | التغيير المطلوب |
|---|---|
| `config/urls.py` | إضافة `path('notifications/', include('notifications.urls'))` |
| `config/settings.py` | إضافة `'notifications'` إلى `INSTALLED_APPS` |
| `templates/includes/sidebar.html` | إضافة جزء الجرس مع HTMX polling |
| `templates/base.html` | إضافة منطقة Toast (OOB swap target) |

**لا يوجد تعديل** على أي ملف في `service_requests/` أو `claims/`.

---

## 10. اعتبارات الأمان

- جميع views محمية بـ `@login_required`
- المستخدم يرى إشعاراته فقط — فلترة صارمة بـ `recipient=request.user`
- `compose/` يتحقق من الدور قبل عرض النموذج وقبل الحفظ
- `reply/` يتحقق أن `request.user` هو `recipient` للرسالة الأصلية
- مرفقات الرسائل تُحفظ بمسارات عشوائية (UUID) بدون الاسم الأصلي

---

## 11. إعداد الـ Admin

`GenericForeignKey` تُبطئ Django Admin إذا كبرت قاعدة البيانات (تحاول تحميل كل الكائنات في dropdown). الإعداد الصحيح:

```python
class NotificationAdmin(admin.ModelAdmin):
    # raw_id_fields على حقول FK فقط (recipient, content_type) — لا يعمل على UUIDField
    raw_id_fields = ('recipient', 'content_type')
    readonly_fields = ('content_object',)   # GenericFK — عرض فقط، بلا dropdown
    list_per_page = 25                       # تحديد عدد الصفوف لتسريع القوائم
    list_select_related = True
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')

class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('sender', 'recipient', 'parent', 'content_type')
    readonly_fields = ('content_object',)
    list_per_page = 25
    list_select_related = True
```

---

## 11. قرارات مؤجلة (للمستقبل)

| الموضوع | الملاحظة |
|---|---|
| بريد إلكتروني | يُضاف في `NotificationService` بسطر واحد لاحقاً دون تغيير Signals |
| Celery | يُستخدم عند إضافة بريد/SMS — البنية جاهزة لذلك |
| WebSocket | يُستبدل polling بـ Django Channels لاحقاً دون تغيير النماذج |
| إشعارات Push | تحتاج Service Worker — مرحلة منفصلة |
