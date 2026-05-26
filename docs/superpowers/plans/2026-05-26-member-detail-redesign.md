# Member Detail Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the member detail page to show stats, a tabbed interface (Dependents / Requests / Claims loaded lazily via HTMX), and enable one-click creation of requests/claims with the member pre-filled.

**Architecture:** The member detail view computes stats and renders the redesigned template. Three new partial-only views serve each tab's content via HTMX. The existing `request_create` and `claim_create` views accept a `?member_id=` query param that pre-selects the member silently.

**Tech Stack:** Django 4.2, HTMX 1.x, Alpine.js 3.x, Tailwind CSS 3.4, Phosphor Icons (ph-duotone)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `members/views.py` | Modify + Add | Extend `member_detail` with stats; add 3 tab views |
| `members/urls.py` | Modify | Register 3 tab URL routes |
| `templates/members/member_detail.html` | Rewrite | Full redesign with stats + tab shell |
| `templates/members/partials/tab_dependents.html` | Create | Dependents tab partial |
| `templates/members/partials/tab_requests.html` | Create | Requests tab partial |
| `templates/members/partials/tab_claims.html` | Create | Claims tab partial |
| `service_requests/views.py` | Modify | Read `?member_id=` in `request_create` GET |
| `templates/service_requests/request_create.html` | Modify | Show pre-filled member card; hide search |
| `claims/views.py` | Modify | Read `?member_id=` in `claim_create` GET |
| `templates/claims/claim_create.html` | Modify | Show pre-filled member card; hide search |

---

## Task 1: Extend `member_detail` view with stats + add 3 tab views

**Files:**
- Modify: `members/views.py`

### Context

The existing `member_detail` view (around line 95) is:
```python
def member_detail(request, pk):
    member = get_object_or_404(
        get_allowed_members(request.user).select_related(
            'client', 'policy_class__policy', 'policy_class__network', 'sponsor'
        ), pk=pk
    )
    dependents = member.dependents.select_related('policy_class').all()
    return render(request, 'members/member_detail.html', {
        'member': member,
        'dependents': dependents
    })
```

- [ ] **Step 1: Add imports to `members/views.py`**

At the top of `members/views.py`, add these imports (after existing imports):

```python
from service_requests.models import ServiceRequest
from claims.models import Claim
```

- [ ] **Step 2: Replace `member_detail` view**

Replace the entire `member_detail` function with:

```python
@login_required
@permission_required('members.view_member', raise_exception=True)
def member_detail(request, pk):
    """
    تفاصيل العضو مع إحصائيات وتابات
    """
    member = get_object_or_404(
        get_allowed_members(request.user).select_related(
            'client', 'policy_class__policy', 'policy_class__network', 'sponsor'
        ),
        pk=pk
    )

    # إحصائيات سريعة
    pending_statuses = [
        ServiceRequest.Status.DRAFT,
        ServiceRequest.Status.SUBMITTED,
        ServiceRequest.Status.HR_REVIEW,
        ServiceRequest.Status.IN_REVIEW,
    ]
    requests_total = member.service_requests.count()
    requests_pending = member.service_requests.filter(status__in=pending_statuses).count()
    claims_total = member.claims.count()
    claims_rejected = member.claims.filter(status=Claim.Status.REJECTED_BY_INSURANCE).count()
    stats = {
        'requests_total': requests_total,
        'requests_pending': requests_pending,
        'requests_done': requests_total - requests_pending,
        'claims_total': claims_total,
        'claims_rejected': claims_rejected,
        'claims_other': claims_total - claims_rejected,
    }

    # التاب الافتراضي: التابعين للموظف، الطلبات للتابع
    default_tab = 'dependents' if member.relation == 'PRINCIPAL' else 'requests'

    return render(request, 'members/member_detail.html', {
        'member': member,
        'stats': stats,
        'default_tab': default_tab,
    })
```

- [ ] **Step 3: Add the 3 tab views at the end of `members/views.py`**

Append these 3 functions after the existing views (before any final URL-related code):

```python
# ==========================================
# Tab Partials — HTMX lazy loading
# ==========================================

@login_required
@permission_required('members.view_member', raise_exception=True)
def member_tab_dependents(request, pk):
    member = get_object_or_404(get_allowed_members(request.user), pk=pk)
    dependents = member.dependents.select_related('policy_class').order_by('full_name')
    return render(request, 'members/partials/tab_dependents.html', {
        'member': member,
        'dependents': dependents,
    })


@login_required
@permission_required('members.view_member', raise_exception=True)
def member_tab_requests(request, pk):
    member = get_object_or_404(get_allowed_members(request.user), pk=pk)
    service_requests = member.service_requests.select_related('request_type').order_by('-created_at')
    return render(request, 'members/partials/tab_requests.html', {
        'member': member,
        'service_requests': service_requests,
    })


@login_required
@permission_required('members.view_member', raise_exception=True)
def member_tab_claims(request, pk):
    member = get_object_or_404(get_allowed_members(request.user), pk=pk)
    claims = member.claims.order_by('-created_at')
    return render(request, 'members/partials/tab_claims.html', {
        'member': member,
        'claims': claims,
    })
```

- [ ] **Step 4: Check for import errors**

```
cd d:\apps\ap
venv\Scripts\Activate.ps1
python manage.py check members
```
Expected output: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```
git add members/views.py
git commit -m "feat(members): add stats and tab views to member_detail"
```

---

## Task 2: Register tab URLs in `members/urls.py`

**Files:**
- Modify: `members/urls.py`

- [ ] **Step 1: Add tab routes**

In `members/urls.py`, inside `urlpatterns`, add these 3 paths after the `member_delete` route (currently line 10):

```python
    # Tab Partials (HTMX)
    path('<uuid:pk>/tabs/dependents/', views.member_tab_dependents, name='member_tab_dependents'),
    path('<uuid:pk>/tabs/requests/', views.member_tab_requests, name='member_tab_requests'),
    path('<uuid:pk>/tabs/claims/', views.member_tab_claims, name='member_tab_claims'),
```

- [ ] **Step 2: Verify URL registration**

```
python manage.py show_urls 2>$null | Select-String "tabs"
```
Expected: 3 lines containing `member_tab_dependents`, `member_tab_requests`, `member_tab_claims`.

- [ ] **Step 3: Commit**

```
git add members/urls.py
git commit -m "feat(members): register tab partial URL routes"
```

---

## Task 3: Rewrite `member_detail.html`

**Files:**
- Rewrite: `templates/members/member_detail.html`

Replace the entire file with:

```django
{% extends 'base.html' %}

{% block content %}
<div class="max-w-6xl mx-auto space-y-8">

    {# ─── HEADER ─────────────────────────────────────────────── #}
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="flex items-center gap-4">
            <a href="{% url 'members:member_list' %}"
                class="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-400 hover:text-brand-600 transition-all shadow-sm">
                <i class="ph-bold ph-arrow-right"></i>
            </a>
            <div>
                <div class="flex items-center gap-3 flex-wrap">
                    <h2 class="text-3xl font-black text-slate-800">{{ member.full_name }}</h2>
                    {% if member.is_active %}
                    <span class="bg-green-50 text-green-600 text-[10px] font-black uppercase px-2 py-0.5 rounded border border-green-100">نشط</span>
                    {% else %}
                    <span class="bg-slate-100 text-slate-400 text-[10px] font-black uppercase px-2 py-0.5 rounded border border-slate-200">معلق</span>
                    {% endif %}
                </div>
                <p class="text-slate-500 font-medium mt-1">
                    {{ member.get_relation_display }} | {{ member.client.name_ar }}
                </p>
            </div>
        </div>
        <div class="flex gap-2">
            {% if perms.members.change_member %}
            <a href="{% url 'members:member_update' member.pk %}"
                class="px-5 py-2.5 bg-white border border-slate-200 text-slate-600 hover:text-brand-600 hover:border-brand-500 rounded-xl font-bold transition-all shadow-sm flex items-center gap-2">
                <i class="ph-duotone ph-pencil-simple text-brand-600 text-xl"></i> تعديل
            </a>
            {% endif %}
            {% if perms.members.delete_member %}
            <a href="{% url 'members:member_delete' member.pk %}"
                class="px-5 py-2.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-xl font-bold transition-all flex items-center gap-2">
                <i class="ph-duotone ph-trash text-xl"></i> حذف
            </a>
            {% endif %}
        </div>
    </div>

    {# ─── MAIN GRID ────────────────────────────────────────────── #}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">

        {# LEFT: Personal Info + Stats (2/3) #}
        <div class="lg:col-span-2 space-y-6">

            {# Personal Info Card #}
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div class="p-6 border-b border-slate-100 bg-slate-50/50">
                    <h3 class="font-black text-slate-800 flex items-center gap-2">
                        <i class="ph-duotone ph-identification-card text-brand-600 text-2xl"></i>
                        البيانات الشخصية
                    </h3>
                </div>
                <div class="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">رقم الهوية / الإقامة</label>
                        <p class="text-slate-800 font-bold text-lg font-mono">{{ member.national_id }}</p>
                    </div>
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">رقم البطاقة الطبية</label>
                        <p class="text-slate-800 font-bold text-lg font-mono">{{ member.medical_card_number }}</p>
                    </div>
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">تاريخ الميلاد</label>
                        <p class="text-slate-700 font-bold">{{ member.birth_date|date:"Y-m-d" }}</p>
                    </div>
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">الجنس</label>
                        <p class="text-slate-700 font-bold">{{ member.get_gender_display }}</p>
                    </div>
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">رقم الجوال</label>
                        <p class="text-slate-700 font-bold">{{ member.phone_number }}</p>
                    </div>
                    <div>
                        <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">العلاقة</label>
                        <p class="text-slate-700 font-bold">{{ member.get_relation_display }}</p>
                    </div>
                </div>

                {# Quick Stats Row #}
                <div class="px-8 pb-8 grid grid-cols-2 gap-4">
                    <div class="bg-slate-50 rounded-xl border border-slate-200 p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <i class="ph-duotone ph-paper-plane-tilt text-brand-600 text-xl"></i>
                            <span class="text-xs font-black text-slate-500 uppercase tracking-wider">الطلبات</span>
                        </div>
                        <p class="text-2xl font-black text-slate-800">{{ stats.requests_total }}</p>
                        <p class="text-xs text-slate-500 mt-1">
                            <span class="text-amber-600 font-bold">{{ stats.requests_pending }} معلّقة</span>
                            &nbsp;·&nbsp;
                            <span class="text-green-600 font-bold">{{ stats.requests_done }} منجزة</span>
                        </p>
                    </div>
                    <div class="bg-slate-50 rounded-xl border border-slate-200 p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <i class="ph-duotone ph-hand-coins text-brand-600 text-xl"></i>
                            <span class="text-xs font-black text-slate-500 uppercase tracking-wider">المطالبات</span>
                        </div>
                        <p class="text-2xl font-black text-slate-800">{{ stats.claims_total }}</p>
                        <p class="text-xs text-slate-500 mt-1">
                            <span class="text-red-500 font-bold">{{ stats.claims_rejected }} مرفوضة</span>
                            &nbsp;·&nbsp;
                            <span class="text-green-600 font-bold">{{ stats.claims_other }} أخرى</span>
                        </p>
                    </div>
                </div>
            </div>

            {# ─── TABS SHELL ────────────────────────────────────── #}
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
                 x-data="{ activeTab: '{{ default_tab }}' }">

                {# Tab Bar #}
                <div class="flex border-b border-slate-200 bg-slate-50/50">
                    {% if member.relation == 'PRINCIPAL' %}
                    <button
                        @click="activeTab = 'dependents'"
                        hx-get="{% url 'members:member_tab_dependents' member.pk %}"
                        hx-target="#tab-content"
                        hx-swap="innerHTML"
                        :class="activeTab === 'dependents' ? 'border-brand-600 text-brand-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-700'"
                        class="flex items-center gap-2 px-6 py-4 text-sm font-black border-b-2 transition-all -mb-px">
                        <i class="ph-duotone ph-users text-lg"></i>
                        التابعون
                    </button>
                    {% endif %}
                    <button
                        @click="activeTab = 'requests'"
                        hx-get="{% url 'members:member_tab_requests' member.pk %}"
                        hx-target="#tab-content"
                        hx-swap="innerHTML"
                        :class="activeTab === 'requests' ? 'border-brand-600 text-brand-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-700'"
                        class="flex items-center gap-2 px-6 py-4 text-sm font-black border-b-2 transition-all -mb-px">
                        <i class="ph-duotone ph-paper-plane-tilt text-lg"></i>
                        الطلبات
                    </button>
                    <button
                        @click="activeTab = 'claims'"
                        hx-get="{% url 'members:member_tab_claims' member.pk %}"
                        hx-target="#tab-content"
                        hx-swap="innerHTML"
                        :class="activeTab === 'claims' ? 'border-brand-600 text-brand-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-700'"
                        class="flex items-center gap-2 px-6 py-4 text-sm font-black border-b-2 transition-all -mb-px">
                        <i class="ph-duotone ph-hand-coins text-lg"></i>
                        المطالبات
                    </button>
                </div>

                {# Tab Content — default tab rendered server-side #}
                <div id="tab-content">
                    {% if default_tab == 'dependents' %}
                        {% include 'members/partials/tab_dependents.html' %}
                    {% else %}
                        {% include 'members/partials/tab_requests.html' %}
                    {% endif %}
                </div>
            </div>
        </div>

        {# RIGHT: Insurance + Sponsor sidebar (1/3) #}
        <div class="space-y-6">
            {# Insurance Coverage Card #}
            <div class="bg-indigo-900 rounded-2xl p-8 text-white relative overflow-hidden shadow-xl shadow-indigo-900/30">
                <div class="relative z-10">
                    <h4 class="text-[10px] font-black text-indigo-300 uppercase tracking-widest mb-6">التغطية التأمينية</h4>
                    <div class="mb-6">
                        <span class="block text-3xl font-black mb-1">{{ member.policy_class.name }}</span>
                        <span class="text-xs text-indigo-300 font-medium">الحد السنوي العام:
                            {{ member.policy_class.annual_limit|floatformat:0 }} SAR</span>
                    </div>
                    <div class="space-y-4 pt-6 border-t border-indigo-800">
                        <div class="flex justify-between items-center text-sm">
                            <span class="text-indigo-400">الشبكة الطبية</span>
                            <span class="font-black">{{ member.policy_class.network.name_ar|default:"-" }}</span>
                        </div>
                        <div class="flex justify-between items-center text-sm">
                            <span class="text-indigo-400">مزود الخدمة</span>
                            <span class="font-black">{{ member.policy_class.policy.provider.name_ar|default:"-" }}</span>
                        </div>
                    </div>
                </div>
                <i class="ph-duotone ph-shield-check absolute -bottom-10 -left-10 text-9xl text-white/5"></i>
            </div>

            {# Sponsor Card (dependents only) #}
            {% if member.sponsor %}
            <div class="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">بيانات الموظف الكفيل</h4>
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                        <i class="ph-duotone ph-user text-2xl"></i>
                    </div>
                    <div>
                        <a href="{% url 'members:member_detail' member.sponsor.pk %}"
                            class="block font-black text-slate-800 hover:text-brand-600 transition">
                            {{ member.sponsor.full_name }}</a>
                        <span class="text-[10px] text-slate-400 font-bold uppercase">
                            {{ member.sponsor.medical_card_number }}</span>
                    </div>
                </div>
            </div>
            {% endif %}
        </div>

    </div>
</div>
{% endblock %}
```

- [ ] **Step 1: Replace `templates/members/member_detail.html`** with the code above (full file replacement).

- [ ] **Step 2: Verify page loads**

With the dev server running, navigate to any member detail page. Confirm:
- Header shows correctly
- Stats cards are visible (may show 0 if no data — that's fine)
- Tab bar appears
- Default tab content loads (server-rendered on first load)
- Clicking other tabs triggers HTMX loads (check network tab in browser DevTools)

- [ ] **Step 3: Commit**

```
git add templates/members/member_detail.html
git commit -m "feat(members): redesign member_detail with stats and tab shell"
```

---

## Task 4: Create the 3 tab partial templates

**Files:**
- Create: `templates/members/partials/tab_dependents.html`
- Create: `templates/members/partials/tab_requests.html`
- Create: `templates/members/partials/tab_claims.html`

Note: The `templates/members/partials/` directory already exists (check with `Test-Path templates/members/partials`). If not, create it.

- [ ] **Step 1: Create `templates/members/partials/tab_dependents.html`**

```django
<div class="p-6">
    <div class="flex items-center justify-between mb-4">
        <h4 class="font-black text-slate-700 flex items-center gap-2">
            <i class="ph-duotone ph-users text-brand-600 text-xl"></i>
            التابعون ({{ dependents.count }})
        </h4>
        {% if perms.members.add_member %}
        <a href="{% url 'members:member_create' %}?sponsor_id={{ member.pk }}&client_id={{ member.client.pk }}&relation=SPOUSE"
            class="px-4 py-2 bg-brand-600 text-white rounded-xl hover:bg-brand-700 text-xs font-black transition-all flex items-center gap-2">
            <i class="ph-bold ph-plus"></i> إضافة تابع
        </a>
        {% endif %}
    </div>

    {% if dependents %}
    <div class="overflow-x-auto rounded-xl border border-slate-200">
        <table class="w-full text-right text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
                <tr>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">الاسم</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">العلاقة</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">رقم البطاقة</th>
                    <th class="px-5 py-3"></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for dep in dependents %}
                <tr class="hover:bg-slate-50 transition group">
                    <td class="px-5 py-3 font-bold text-slate-800">{{ dep.full_name }}</td>
                    <td class="px-5 py-3 text-center">
                        <span class="text-[10px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-black">
                            {{ dep.get_relation_display }}</span>
                    </td>
                    <td class="px-5 py-3 text-center font-mono text-slate-500">{{ dep.medical_card_number }}</td>
                    <td class="px-5 py-3 text-left">
                        <a href="{% url 'members:member_detail' dep.pk %}"
                            class="opacity-0 group-hover:opacity-100 text-brand-600 hover:underline font-bold text-xs">عرض</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="py-16 text-center">
        <i class="ph-duotone ph-users text-5xl text-slate-300 mb-3 block"></i>
        <p class="text-slate-400 font-medium">لا يوجد تابعون مسجلون لهذا الموظف</p>
    </div>
    {% endif %}
</div>
```

- [ ] **Step 2: Create `templates/members/partials/tab_requests.html`**

```django
<div class="p-6">
    <div class="flex items-center justify-between mb-4">
        <h4 class="font-black text-slate-700 flex items-center gap-2">
            <i class="ph-duotone ph-paper-plane-tilt text-brand-600 text-xl"></i>
            الطلبات ({{ service_requests.count }})
        </h4>
        {% if perms.service_requests.can_submit_service_request %}
        <a href="{% url 'service_requests:request_create' %}?member_id={{ member.pk }}"
            class="px-4 py-2 bg-brand-600 text-white rounded-xl hover:bg-brand-700 text-xs font-black transition-all flex items-center gap-2">
            <i class="ph-bold ph-plus"></i> طلب جديد
        </a>
        {% endif %}
    </div>

    {% if service_requests %}
    <div class="overflow-x-auto rounded-xl border border-slate-200">
        <table class="w-full text-right text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
                <tr>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">المرجع</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">نوع الطلب</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">الحالة</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">التاريخ</th>
                    <th class="px-5 py-3"></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for req in service_requests %}
                <tr class="hover:bg-slate-50 transition group">
                    <td class="px-5 py-3 font-mono text-xs text-slate-600 font-bold">{{ req.reference }}</td>
                    <td class="px-5 py-3 font-medium text-slate-800">{{ req.request_type.name_ar }}</td>
                    <td class="px-5 py-3 text-center">
                        {% if req.status == 'RESOLVED' %}
                            <span class="text-[10px] bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-100 font-black">{{ req.get_status_display }}</span>
                        {% elif req.status == 'REJECTED' %}
                            <span class="text-[10px] bg-red-50 text-red-700 px-2 py-0.5 rounded border border-red-100 font-black">{{ req.get_status_display }}</span>
                        {% elif req.status == 'DRAFT' %}
                            <span class="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200 font-black">{{ req.get_status_display }}</span>
                        {% else %}
                            <span class="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100 font-black">{{ req.get_status_display }}</span>
                        {% endif %}
                    </td>
                    <td class="px-5 py-3 text-center text-slate-500 text-xs">{{ req.created_at|date:"Y-m-d" }}</td>
                    <td class="px-5 py-3 text-left">
                        <a href="{% url 'service_requests:request_detail' req.pk %}"
                            class="opacity-0 group-hover:opacity-100 text-brand-600 hover:underline font-bold text-xs">عرض</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="py-16 text-center">
        <i class="ph-duotone ph-paper-plane-tilt text-5xl text-slate-300 mb-3 block"></i>
        <p class="text-slate-400 font-medium">لا توجد طلبات مسجلة لهذا العضو</p>
    </div>
    {% endif %}
</div>
```

- [ ] **Step 3: Create `templates/members/partials/tab_claims.html`**

```django
<div class="p-6">
    <div class="flex items-center justify-between mb-4">
        <h4 class="font-black text-slate-700 flex items-center gap-2">
            <i class="ph-duotone ph-hand-coins text-brand-600 text-xl"></i>
            المطالبات ({{ claims.count }})
        </h4>
        {% if perms.claims.can_submit_claim %}
        <a href="{% url 'claims:claim_create' %}?member_id={{ member.pk }}"
            class="px-4 py-2 bg-brand-600 text-white rounded-xl hover:bg-brand-700 text-xs font-black transition-all flex items-center gap-2">
            <i class="ph-bold ph-plus"></i> مطالبة جديدة
        </a>
        {% endif %}
    </div>

    {% if claims %}
    <div class="overflow-x-auto rounded-xl border border-slate-200">
        <table class="w-full text-right text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
                <tr>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">المرجع</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">المبلغ</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">الحالة</th>
                    <th class="px-5 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest text-center">التاريخ</th>
                    <th class="px-5 py-3"></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for claim in claims %}
                <tr class="hover:bg-slate-50 transition group">
                    <td class="px-5 py-3 font-mono text-xs text-slate-600 font-bold">{{ claim.claim_reference }}</td>
                    <td class="px-5 py-3 text-center font-bold text-slate-800">{{ claim.amount_original|floatformat:2 }} {{ claim.currency_id }}</td>
                    <td class="px-5 py-3 text-center">
                        {% if claim.status == 'PAID' or claim.status == 'APPROVED_BY_INSURANCE' %}
                            <span class="text-[10px] bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-100 font-black">{{ claim.get_status_display }}</span>
                        {% elif claim.status == 'REJECTED_BY_INSURANCE' %}
                            <span class="text-[10px] bg-red-50 text-red-700 px-2 py-0.5 rounded border border-red-100 font-black">{{ claim.get_status_display }}</span>
                        {% elif claim.status == 'DRAFT' %}
                            <span class="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200 font-black">{{ claim.get_status_display }}</span>
                        {% else %}
                            <span class="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100 font-black">{{ claim.get_status_display }}</span>
                        {% endif %}
                    </td>
                    <td class="px-5 py-3 text-center text-slate-500 text-xs">{{ claim.created_at|date:"Y-m-d" }}</td>
                    <td class="px-5 py-3 text-left">
                        <a href="{% url 'claims:claim_detail' claim.pk %}"
                            class="opacity-0 group-hover:opacity-100 text-brand-600 hover:underline font-bold text-xs">عرض</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="py-16 text-center">
        <i class="ph-duotone ph-hand-coins text-5xl text-slate-300 mb-3 block"></i>
        <p class="text-slate-400 font-medium">لا توجد مطالبات مسجلة لهذا العضو</p>
    </div>
    {% endif %}
</div>
```

- [ ] **Step 4: Verify in browser**

Navigate to a member detail page. Click each tab and confirm:
- Content loads without a full page reload
- Empty states display when no data
- "إضافة" buttons are visible (permissions permitting)

- [ ] **Step 5: Commit**

```
git add templates/members/partials/tab_dependents.html templates/members/partials/tab_requests.html templates/members/partials/tab_claims.html
git commit -m "feat(members): add tab partial templates"
```

---

## Task 5: Pre-fill member in `service_requests:request_create`

**Files:**
- Modify: `service_requests/views.py` (the `request_create` function)
- Modify: `templates/service_requests/request_create.html`

### Step 1: Modify `request_create` view (GET block only)

In `service_requests/views.py`, locate `request_create`. Add `prefilled_member = None` at the very top of the function body (before the `if request.method == 'POST':` check), then in the `else` block (GET), replace:

```python
    else:
        form = ServiceRequestCreateForm(user=user)
    
    return render(request, 'service_requests/request_create.html', {
        'form': form, 'request_types': request_types,
    })
```

with:

```python
    else:
        member_id = request.GET.get('member_id')
        if member_id:
            from members.models import Member
            from members.views import get_allowed_members
            prefilled_member = get_allowed_members(request.user).filter(pk=member_id).first()
        form = ServiceRequestCreateForm(user=user)

    return render(request, 'service_requests/request_create.html', {
        'form': form,
        'request_types': request_types,
        'prefilled_member': prefilled_member,
    })
```

> **Note:** `prefilled_member` is defined as `None` at the top of the function so it is always defined (even on POST). It is only used for GET display — the actual member is resolved by `national_id_search` in form `clean()` regardless.

- [ ] **Step 1:** Apply the view change above.

- [ ] **Step 2: Modify the template `templates/service_requests/request_create.html`**

Find the section for HR/Broker member search (starts around `{% else %}` after `{% if user.is_member_role %}`):

```django
                {% else %}
                <!-- HR / Broker / SuperAdmin View: NID search -->
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">بحث برقم الهوية للمستفيد <span class="text-red-500">*</span></label>
                    <div class="relative">
                        <i class="ph-duotone ph-magnifying-glass absolute top-2.5 right-3 text-slate-400"></i>
                        <input type="text" name="national_id_search"
                               hx-get="{% url 'service_requests:search_member' %}"
                               hx-trigger="keyup changed delay:500ms"
                               hx-target="#search-result"
                               placeholder="أدخل رقم الهوية للبحث..."
                               class="w-full pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition {% if form.national_id_search.errors %}border-red-500{% endif %}">
                    </div>
                    {% if form.national_id_search.errors %}
                        <p class="text-red-500 text-sm mt-1">{{ form.national_id_search.errors.0 }}</p>
                    {% endif %}
                    <div id="search-result"></div>
                </div>
                {% endif %}
```

Replace it with:

```django
                {% else %}
                <!-- HR / Broker / SuperAdmin View -->
                {% if prefilled_member %}
                <!-- Pre-filled from member detail page -->
                <div class="p-3 bg-brand-50 border border-brand-200 rounded-md flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="h-10 w-10 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-bold border border-brand-200">
                            <i class="ph-duotone ph-user text-xl"></i>
                        </div>
                        <div>
                            <p class="font-bold text-slate-800">{{ prefilled_member.full_name }}</p>
                            <p class="text-xs text-slate-500">
                                {{ prefilled_member.get_relation_display }} • {{ prefilled_member.client.name_ar }}
                            </p>
                        </div>
                    </div>
                    <i class="ph-fill ph-check-circle text-brand-500 text-2xl"></i>
                </div>
                <input type="hidden" name="national_id_search" value="{{ prefilled_member.national_id }}">
                <input type="hidden" name="member" value="{{ prefilled_member.pk }}">
                {% else %}
                <!-- Normal NID search -->
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">بحث برقم الهوية للمستفيد <span class="text-red-500">*</span></label>
                    <div class="relative">
                        <i class="ph-duotone ph-magnifying-glass absolute top-2.5 right-3 text-slate-400"></i>
                        <input type="text" name="national_id_search"
                               hx-get="{% url 'service_requests:search_member' %}"
                               hx-trigger="keyup changed delay:500ms"
                               hx-target="#search-result"
                               placeholder="أدخل رقم الهوية للبحث..."
                               class="w-full pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition {% if form.national_id_search.errors %}border-red-500{% endif %}">
                    </div>
                    {% if form.national_id_search.errors %}
                        <p class="text-red-500 text-sm mt-1">{{ form.national_id_search.errors.0 }}</p>
                    {% endif %}
                    <div id="search-result"></div>
                </div>
                {% endif %}
                {% endif %}
```

- [ ] **Step 3: Test pre-fill manually**

1. Navigate to a member detail page
2. Click the "Requests" tab
3. Click "طلب جديد"
4. Confirm the request_create page shows the member card (green banner) instead of the NID search input
5. Submit the form and confirm the request is created for that member

- [ ] **Step 4: Commit**

```
git add service_requests/views.py templates/service_requests/request_create.html
git commit -m "feat(service_requests): pre-fill member when coming from member detail"
```

---

## Task 6: Pre-fill member in `claims:claim_create`

**Files:**
- Modify: `claims/views.py` (the `claim_create` function)
- Modify: `templates/claims/claim_create.html`

### Step 1: Modify `claim_create` view

In `claims/views.py`, locate `claim_create`. Add `prefilled_member = None` at the very top of the function body (before `if request.method == 'POST':`), then in the `else` block (GET), replace:

```python
    else:
        form = ClaimCreateForm(user=request.user)

    return render(request, 'claims/claim_create.html', {'form': form})
```

with:

```python
    else:
        member_id = request.GET.get('member_id')
        if member_id:
            from members.models import Member
            from members.views import get_allowed_members
            prefilled_member = get_allowed_members(request.user).filter(pk=member_id).first()
        form = ClaimCreateForm(user=request.user)

    context = {
        'form': form,
        'prefilled_member': prefilled_member,
    }
    return render(request, 'claims/claim_create.html', context)
```

> **Note:** `prefilled_member = None` is set at the top of the function so it is always defined (even on POST).

- [ ] **Step 1:** Apply the view change above.

- [ ] **Step 2: Modify the template `templates/claims/claim_create.html`**

Find the HR View section (after `{% if user.role == 'HR' or perms.accounts.view_hr_dashboard %}`):

```django
                {% if user.role == 'HR' or perms.accounts.view_hr_dashboard %}
                <!-- HR View -->
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">بحث برقم الهوية للمستفيد <span class="text-red-500">*</span></label>
                    <div class="relative">
                        <i class="ph-duotone ph-magnifying-glass absolute top-2.5 right-3 text-slate-400"></i>
                        <input type="text" name="{{ form.national_id_search.html_name }}" 
                               hx-get="{% url 'claims:search_member_by_nid' %}"
                               hx-trigger="keyup changed delay:500ms"
                               hx-target="#search-result"
                               placeholder="أدخل رقم الهوية للبحث..."
                               class="w-full pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition {% if form.national_id_search.errors %}border-red-500{% endif %}">
                    </div>
                    {% if form.national_id_search.errors %}
                        <p class="text-red-500 text-sm mt-1">{{ form.national_id_search.errors.0 }}</p>
                    {% endif %}
                    <div id="search-result"></div>
                </div>
```

Replace it with:

```django
                {% if user.role == 'HR' or perms.accounts.view_hr_dashboard %}
                <!-- HR / Broker / Admin View -->
                {% if prefilled_member %}
                <!-- Pre-filled from member detail page -->
                <div class="p-3 bg-brand-50 border border-brand-200 rounded-md flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="h-10 w-10 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-bold border border-brand-200">
                            <i class="ph-duotone ph-user text-xl"></i>
                        </div>
                        <div>
                            <p class="font-bold text-slate-800">{{ prefilled_member.full_name }}</p>
                            <p class="text-xs text-slate-500">
                                {{ prefilled_member.get_relation_display }} • {{ prefilled_member.client.name_ar }}
                            </p>
                        </div>
                    </div>
                    <i class="ph-fill ph-check-circle text-brand-500 text-2xl"></i>
                </div>
                <input type="hidden" name="{{ form.national_id_search.html_name }}" value="{{ prefilled_member.national_id }}">
                <input type="hidden" name="{{ form.member.html_name }}" value="{{ prefilled_member.pk }}">
                {% else %}
                <!-- Normal NID search -->
                <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">بحث برقم الهوية للمستفيد <span class="text-red-500">*</span></label>
                    <div class="relative">
                        <i class="ph-duotone ph-magnifying-glass absolute top-2.5 right-3 text-slate-400"></i>
                        <input type="text" name="{{ form.national_id_search.html_name }}" 
                               hx-get="{% url 'claims:search_member_by_nid' %}"
                               hx-trigger="keyup changed delay:500ms"
                               hx-target="#search-result"
                               placeholder="أدخل رقم الهوية للبحث..."
                               class="w-full pl-4 pr-10 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition {% if form.national_id_search.errors %}border-red-500{% endif %}">
                    </div>
                    {% if form.national_id_search.errors %}
                        <p class="text-red-500 text-sm mt-1">{{ form.national_id_search.errors.0 }}</p>
                    {% endif %}
                    <div id="search-result"></div>
                </div>
                {% endif %}
```

- [ ] **Step 3: Test pre-fill manually**

1. Navigate to a member detail page
2. Click the "Claims" tab
3. Click "مطالبة جديدة"
4. Confirm the claim_create page shows the member card (green banner)
5. Submit the form and confirm the claim is created for that member

- [ ] **Step 4: Final system check**

```
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```
git add claims/views.py templates/claims/claim_create.html
git commit -m "feat(claims): pre-fill member when coming from member detail"
```

---

## Done

All 6 tasks complete. The member detail page now shows:
- Personal info + quick stats (requests pending, claims rejected)
- Insurance coverage sidebar
- Sponsor card for dependents
- HTMX lazy-loaded tabs: Dependents (PRINCIPAL only) / Requests / Claims
- One-click "Add" buttons in each tab with member pre-filled in the target form
