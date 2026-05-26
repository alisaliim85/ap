# Member Detail Page Redesign — Design Spec
**Date:** 2026-05-26  
**Status:** Approved  
**Scope:** `members` app — detail page only  

---

## 1. Goal

Redesign `member_detail.html` to present a richer, role-aware profile page that lets admins view personal data, insurance coverage stats, and act on a member (create requests/claims) without leaving the page flow. Improve UX by grouping related data into lazy-loaded tabs and enabling one-click navigation to creation forms with the member pre-filled.

---

## 2. User Roles & Behaviour

This page is accessed by: `SUPER_ADMIN`, `BROKER_ADMIN`, `BROKER_STAFF`, `HR_ADMIN`, `HR_STAFF`. Data isolation is already enforced by `get_allowed_members(user)` in `member_detail` view — no changes needed there.

---

## 3. Page Layout

```
┌────────────────────────────────────────────────────────────┐
│ HEADER: Full name + Active/Suspended badge + Edit/Delete    │
└────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐  ┌───────────────────────────┐
│  Personal Info Card (2/3)    │  │  Insurance Coverage (1/3)  │
│  ─ National ID               │  │  ─ Policy class name       │
│  ─ Medical card #            │  │  ─ Annual limit            │
│  ─ Birth date                │  │  ─ Network name            │
│  ─ Gender                    │  │  ─ Insurance provider      │
│  ─ Phone                     │  │                            │
│  ─ Relation                  │  │  [Dependent only]          │
│                              │  │  Sponsor Card              │
│  Quick Stats Row             │  │  ─ Sponsor name + link     │
│  ┌──────────┐ ┌───────────┐  │  │  ─ Sponsor card #          │
│  │ Requests │ │  Claims   │  │  └───────────────────────────┘
│  │ 5 total  │ │ 4 total   │  │
│  │ 2 pending│ │ 1 rejected│  │
│  └──────────┘ └───────────┘  │
└──────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ TABS (full width)                                          │
│ [التابعون*] [الطلبات] [المطالبات]                           │
│ * التابعون tab shown only when member.relation == PRINCIPAL │
├────────────────────────────────────────────────────────────┤
│ Tab content area (HTMX lazy loaded)                        │
│ Each tab has an "Add" button at top-right                  │
└────────────────────────────────────────────────────────────┘
```

---

## 4. Quick Stats

Computed in `member_detail` view and passed as `stats` dict:

| Key | Definition |
|---|---|
| `requests_total` | `member.service_requests.count()` |
| `requests_pending` | status in `[DRAFT, SUBMITTED, HR_REVIEW, IN_REVIEW]` |
| `claims_total` | `member.claims.count()` |
| `claims_rejected` | status = `REJECTED` |

Displayed as two small stat cards side-by-side inside the personal info section.

---

## 5. Tabs System

### Tab visibility
- **Dependents tab**: shown only when `member.relation == 'PRINCIPAL'`
- **Requests tab**: always shown
- **Claims tab**: always shown

### Default active tab
- If `PRINCIPAL`: Dependents tab is active by default (loaded on page load)
- If dependent: Requests tab is active by default

### Loading mechanism
- Tab switching uses **Alpine.js** for active state tracking
- Content is loaded via **HTMX `hx-get`** to dedicated partial endpoints
- Each tab target is a `<div id="tab-content">` replaced by HTMX
- Tabs trigger on `click`, with `hx-trigger="click"` and a `hx-swap="innerHTML"` on the content div
- To avoid loading the default tab twice, the first tab's content is rendered server-side on the initial page load; subsequent tab clicks use HTMX

### Tab endpoints (new in `members/urls.py`)

```
GET /members/<uuid:pk>/tabs/dependents/  → member_tab_dependents
GET /members/<uuid:pk>/tabs/requests/    → member_tab_requests
GET /members/<uuid:pk>/tabs/claims/      → member_tab_claims
```

All three are protected by `@login_required` and use `get_allowed_members()` for the member lookup (404 if not allowed).

---

## 6. Tab Content Details

### 6a. Dependents Tab
**Template:** `members/partials/tab_dependents.html`

- Table columns: Name | Relation | Medical Card # | View link
- Empty state: icon + message "لا يوجد تابعين مسجلين"
- **Add button** at top-right: links to `members:member_create?sponsor_id={{ member.pk }}&client_id={{ member.client.pk }}&relation=SPOUSE` (existing behaviour, already works)

### 6b. Requests Tab
**Template:** `members/partials/tab_requests.html`

- Table columns: Reference | Request Type | Status badge | Date | View link
- Empty state: icon + message "لا توجد طلبات مسجلة لهذا العضو"
- **Add button** at top-right: links to `service_requests:request_create?member_id={{ member.pk }}`
- Status badge colours follow existing design system (DRAFT=slate, SUBMITTED=blue, RESOLVED=green, REJECTED=red)

### 6c. Claims Tab
**Template:** `members/partials/tab_claims.html`

- Table columns: Reference | Amount (SAR) | Status badge | Date | View link
- Empty state: icon + message "لا توجد مطالبات مسجلة لهذا العضو"
- **Add button** at top-right: links to `claims:claim_create?member_id={{ member.pk }}`

---

## 7. Pre-fill Member in Create Views

Both `service_requests:request_create` and `claims:claim_create` receive a `?member_id=<uuid>` query parameter when accessed from the member detail page.

### Changes to `service_requests/views.py` → `request_create`
On GET: read `request.GET.get('member_id')`. If present:
- Set `initial = {'member': member_id}` on the form
- Pass `prefilled_member_id = member_id` to the template context

In the template `request_create.html`: if `prefilled_member_id` is set, render the member field as hidden (the form still validates it server-side). Show a read-only display of the member name above it.

### Changes to `claims/views.py` → `claim_create`
Identical pattern to above.

**Security note:** The member field queryset is already filtered by `get_allowed_members()` inside the form `__init__` (via `user=` context). Passing a `member_id` from another client will simply fail form validation — no extra check needed.

---

## 8. Files Changed

| File | Change |
|---|---|
| `members/views.py` | Extend `member_detail` to compute `stats`; add `member_tab_dependents`, `member_tab_requests`, `member_tab_claims` views |
| `members/urls.py` | Add 3 tab routes under `tabs/` |
| `templates/members/member_detail.html` | Full redesign per layout above |
| `templates/members/partials/tab_dependents.html` | New partial |
| `templates/members/partials/tab_requests.html` | New partial |
| `templates/members/partials/tab_claims.html` | New partial |
| `service_requests/views.py` | Read `?member_id=` in `request_create` GET; pass to template |
| `templates/service_requests/request_create.html` | Hide member field + show read-only name when pre-filled |
| `claims/views.py` | Read `?member_id=` in `claim_create` GET; pass to template |
| `templates/claims/claim_create.html` | Hide member field + show read-only name when pre-filled |

---

## 9. Out of Scope

- No changes to member model or migrations
- No changes to claims or service_requests models
- No changes to permissions or roles
- Pagination inside tabs is not required for v1 (all records shown, sorted by `-created_at`)
- Search/filter inside tabs is not in scope for v1
