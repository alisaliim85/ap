# AP PLUS - Agent Guide

## What this is

Django 4.2 monolithic app for medical insurance brokerage (B2B2C). Arabic RTL UI. No separate frontend — UI lives in `templates/` and app template folders using Django templates + HTMX + Bootstrap 5 (CDN, not Tailwind in production).

## Commands

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

No test framework, linter, formatter, or CI pipeline is configured. `tests.py` files are stubs.

## Architecture

- **Settings**: `config/settings.py` (env-driven via `python-decouple`)
- **Root URLs**: `config/urls.py` — all app URLs registered here
- **Root path `/`**: serves `accounts.login_view`
- **Custom User model**: `accounts.User` (`AUTH_USER_MODEL = 'accounts.User'`)
- **DB**: SQLite at `db.sqlite3`
- **Timezone**: `Asia/Riyadh`

### Domain apps (in `config/urls.py` order)

| App | Path prefix | Domain |
|-----|------------|--------|
| accounts | `/` | Users, roles, auth, dashboard |
| clients | `/clients/` | Contracting companies (hierarchical) |
| providers | `/providers/` | Insurance companies |
| partners | `/partners/` | Medical service providers (pharmacies, care centers) |
| policies | `/policies/` | Policies, classes, benefits |
| networks | `/networks/` | Hospital/service provider networks |
| members | `/members/` | Insured employees and families |
| claims | `/claims/` | Reimbursement claims workflow |
| brokers | `/brokers/` | Broker operations |
| service-requests | `/service-requests/` | Service requests (reference impl for new features) |
| medications | `/medications/` | Medication management |
| notifications | `/notifications/` | Notification system |

`api` app exists but is not mounted at a top-level URL prefix.

### User roles (from `accounts`)

- **Broker** (Admin, Staff) — full system access
- **HR** (Admin, Staff) — company-scoped access
- **Medical Partner** (Pharmacist, Chronic Staff) — assigned service access

## Conventions (follow `service_requests` as reference)

- **UUID PKs** on all new models: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- **Reference numbers**: auto-generated like `REQ-2026-00001` using `transaction.atomic()` + `select_for_update()`
- **JSONField** for dynamic data
- **Status transitions** with audit logging via `RequestStatusLog`
- **File uploads**: paths include reference number (e.g., `service_requests/docs/REQ-2026-00001/file.pdf`)
- **App namespacing**: each app sets `app_name` in urls.py
- **HTMX**: partial updates, search/filter, dynamic content endpoints
- **Data isolation**: filter functions like `get_allowed_requests(user)` enforce role-based visibility
- **Admin**: inline related models, readonly audit fields

## Sensitive data

- Encrypted fields via `django-encrypted-model-fields` (AES-256): IDs, phones, addresses, medical records
- `.env` contains `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` — never commit
- Preserve encryption semantics when modifying models

## UI conventions (from `DESIGN_SYSTEM_GUIDE.md`)

- Arabic RTL layout, right-aligned sidebar navigation
- Side drawers from LEFT (RTL) for edit/detail views via HTMX
- Phosphor duotone icons
- Responsive: data tables become stacked cards on mobile
