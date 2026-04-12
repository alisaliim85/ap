# Member's Assigned Hospitals Network Feature

## 1. Product Requirements Document (PRD)

### Problem Statement
Insurance members currently lack a dedicated, user-friendly interface to view the specific medical network (hospitals, pharmacies, clinics, etc.) assigned to their medical class. They need an easy way to explore and filter their allocated medical service providers on the go, especially via mobile devices.

### Objectives
- Create a dedicated "قائمة المستشفيات" (Hospitals List) page for members.
- Accurately fetch the medical network associated with the current user's `member_profile.policy_class.network`.
- Implement dynamic filtering by City, Provider Type, and a Search query for names.
- Ensure a Mobile-First, responsive User Experience aligning with the `DESIGN_SYSTEM_GUIDE.md`.

### Target Audience
- System Users with the `MEMBER` role (`User.Roles.MEMBER`).

### Functional Requirements
1. **Access Control**: Only logged-in users with the `MEMBER` role and a valid `Member` profile can access the page.
2. **Data Retrieval**: Display only `ServiceProvider` records that are linked to the user's assigned `Network`.
3. **Filtering & Search**:
    - **Search**: Text search covering `name_ar` and `name_en`.
    - **City Filter**: Dropdown populated with distinct cities found within the member's assigned network.
    - **Type Filter**: Dropdown of provider types (Hospital, Pharmacy, Lab, etc.).
4. **Pagination**: Load a manageable number of providers per page (e.g., 15) to maintain performance.
5. **Responsiveness (Mobile-First)**:
    - Display records as stacked data cards on mobile devices.
    - Display as a clean data table on desktop screens.
    - Use HTMX for seamless filtering without full page reloads to ensure smooth UI/UX.

### Non-Functional Requirements
- **Language**: Strict Arabic (RTL) interface.
- **Design System**: Use predefined Almarai font, Teal/Emerald primary colors, Slate gray backgrounds, and Phosphor icons as instructed.

---

## 2. Milestones

- **Milestone 1**: Backend Implementation (View & URL setup).
- **Milestone 2**: Frontend Structure (Base Template, Mobile/Desktop Layouts).
- **Milestone 3**: UI/UX Refinement & HTMX Integration (Filters, Pagination).
- **Milestone 4**: Testing, Review, and Deployment.

---

## 3. Implementation Tasks

### Task 1: Backend Logic & URL Routing
- **File**: `members/views.py`
  - [NEW] Add `my_hospitals` view.
  - Fetch `request.user.member_profile.policy_class.network.hospitals.all()`.
  - Extract available `cities` for the dropdown.
  - Implement filtering logic using `Q` objects (`search`, `city`, `type`).
  - Add Pagination (`Paginator`).
  - Handle HTMX partial requests to update the layout dynamically.
- **File**: `members/urls.py`
  - [MODIFY] Add URL pattern: `path('my-hospitals/', views.my_hospitals, name='my_hospitals')`.

### Task 2: Base UI & Mobile-First Template
- **File**: `templates/members/my_hospitals.html`
  - [NEW] Create the main template.
  - Include a page header with the title "قائمة المستشفيات".
  - Implement the filter bar (Search box, City select, Type select) using the Tailwind UI patterns specified in the design guide.
  - Add `hx-get`, `hx-target`, and `hx-trigger` attributes to inputs for seamless fetching.
  - Set up the layout: `hidden md:block` for the desktop table and `md:hidden` for the mobile cards.

### Task 3: HTMX Partials & Data Rendering
- **File**: `templates/members/partials/hospital_list_content.html`
  - [NEW] Create a partial template for HTMX to hot-swap.
  - Implement the Desktop variant (`<table>` structure from design system).
  - Implement the Mobile variant (stacked `<div class="card">` structure).
  - Add conditional rendering for Empty States (e.g., "لا توجد مستشفيات مطابقة للبحث").
  - Render pagination controls using HTMX.

---

## User Review Required

> [!IMPORTANT]
> The proposed plan strictly follows the `DESIGN_SYSTEM_GUIDE.md` and uses HTMX for the filtering. On mobile, hospitals will be displayed as distinct cards, and on desktop as structured lists. Please review the PRD, Milestones, and Tasks above, and let me know if you approve this approach so I can start implementation!
