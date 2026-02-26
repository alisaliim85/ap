# System Permissions & Roles Audit Report

## 1. Overview
This document provides a comprehensive inventory of all user Roles, Groups, and Permissions (both standard and custom) identified in the **AP PLUS** project codebase.

## 2. User Roles
The system defines the following roles in `accounts.models.User.Roles`. These roles determine the primary function of a user.

| Role Code | Display Name | Description |
| :--- | :--- | :--- |
| `SUPER_ADMIN` | Super Admin (Owner) | Full system access. |
| `BROKER_ADMIN` | Broker Admin | Admin access for the brokerage firm. |
| `BROKER_STAFF` | Broker Staff | Operational staff for the brokerage firm. |
| `HR_ADMIN` | HR Admin | Administrator for a Client Company. |
| `HR_STAFF` | HR Staff | HR staff for a Client Company. |
| `PHARMACIST` | Pharmacist | Medical partner staff (Pharmacy). |
| `CHRONIC_ADMIN` | Chronic Disease Admin | Admin for Chronic Care Centers. |
| `CHRONIC_STAFF` | Chronic Disease Staff | Doctors/Nurses for Chronic Care. |
| `VIEWER` | Viewer / Auditor | Read-only access (Auditor). |
| `MEMBER` | Member / Beneficiary | The end-user (Employee/Dependent). |

## 3. Groups Strategy
The system uses a **1-to-1 mapping** between **Roles** and **Django Groups**.
- **Logic:** Defined in `accounts.signals.move_user_to_group`.
- **Behavior:** When a user is assigned a `role` (e.g., `HR_ADMIN`), the system automatically adds them to a Django Group with the same name (`HR_ADMIN`) and removes them from other role-based groups.
- **Current State:** Groups are created automatically but **Permissions are NOT assigned to these groups via code**. They must be assigned manually in the Admin Panel or via a data fixture/script.

## 4. Permissions Inventory

### 4.1 Accounts App (`accounts`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `view_broker_dashboard` | Can view Broker Dashboard | Broker Portal Access |
| `view_hr_dashboard` | Can view HR Dashboard | Client/HR Portal Access |
| `view_partner_dashboard` | Can view Partner Dashboard | Medical Partner Portal Access |
| `view_member_dashboard` | Can view Member Dashboard | Member App/Portal Access |
| `manage_users` | Can manage system users | Create/Edit Internal Users |
| `manage_company_staff` | *Undefined in Model* | **Issue:** Used in views/templates but missing in `Meta`. |

### 4.2 Claims App (`claims`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `can_submit_claim` | Can submit new claim | Members |
| `can_approve_hr` | Can approve claim as HR | HR Admin |
| `can_reject_hr` | Can return/reject claim as HR | HR Admin |
| `can_process_broker` | Can process claim as Broker | Broker Staff |
| `can_approve_payment` | Can mark claim as Paid | Broker Admin/Finance |
| `can_view_all_claims` | Can view all claims | Auditors/Managers |
| `view_sensitive_medical_data` | Can view sensitive medical attachments | Medical Staff |
| `view_internal_comments` | Can view internal comments | Broker/HR Internal comms |

### 4.3 Chronic Care App (`chronic_care`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_disease_list` | Can manage disease list configuration | System Config |
| `manage_chronic_requests` | Can create/edit chronic requests | HR/Members |
| `approve_request` | Can approve/reject chronic requests | Broker/Medical Team |
| `assign_partner` | Can assign partner to chronic requests | Broker Operations |
| `manage_chronic_cases` | Can create/edit chronic cases | Care Centers |
| `suspend_case` | Can suspend or terminate chronic cases | Medical Admin |
| `manage_home_visits` | Can create/edit home visits | Scheduling Team |
| `process_visit` | Can start/complete home visits | Field Doctors |
| `view_sensitive_medical_data` | Can view encrypted doctor notes | Doctors/Auditors |
| `upload_lab_result` | Can upload lab test results | Lab Technicians |

### 4.4 Clients App (`clients`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_clients` | Can create/edit clients | Broker Admin |
| `view_client_dashboard` | Can view client dashboard statistics | HR Admin |

**Standard Permissions Used:**
- `clients.view_client`

### 4.5 Members App (`members`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `view_all_members` | Can view members of their company | HR Admin |
| `manage_members` | Can add/edit members | HR Admin/Broker |
| `bulk_upload_members` | Can perform bulk upload | HR Admin |
| `view_my_family_members` | Can view their own family members | Principal Members |

**Standard Permissions Used:**
- `members.view_member`, `members.add_member`, `members.change_member`, `members.delete_member`

### 4.6 Networks App (`networks`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_providers` | Can create/edit providers | Network Team |
| `bulk_upload_providers` | Can upload provider lists via Excel | Network Team |
| `manage_networks` | Can create/edit networks | Network Team |

**Standard Permissions Used:**
- `networks.view_network`, `networks.add_network`, `networks.change_network`, `networks.delete_network`
- `networks.view_serviceprovider`, `networks.add_serviceprovider`...

### 4.7 Partners App (`partners`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_partners` | Can create/edit partners | Broker Admin |
| `view_partner_contracts` | Can view/download sensitive contract files | Legal/Admin |

**Standard Permissions Used:**
- `partners.view_partner`, `partners.add_partner`...

### 4.8 Policies App (`policies`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_benefit_types` | Can create/edit benefit types | Product Team |
| `manage_policy_structure` | Can create/edit policies and classes | Underwriting Team |
| `view_policy_details` | Can view policy coverage details | HR/Broker/Members |

**Standard Permissions Used:**
- `policies.view_policy`, `policies.add_policy`, `policies.change_policy`, `policies.delete_policy`

### 4.9 Providers App (`providers`)
**Custom Permissions:**
| Codename | Description | Usage |
| :--- | :--- | :--- |
| `manage_insurance_companies` | Can create/edit insurance companies | Broker Admin |

**Standard Permissions Used:**
- `providers.view_provider`, `providers.add_provider`...

## 5. Audit Findings & Recommendations
1.  **Missing Permission Definition:** The permission `accounts.manage_company_staff` is actively used in `accounts/views.py` (for HR user management) and the sidebar template, but it is **NOT defined** in `accounts.models.User.Meta`.
    - *Impact:* Checking this permission (`user.has_perm`) will always return `False` (unless created manually in DB), potentially locking HR Admins out of managing their staff.
    - *Action Required:* Add `("manage_company_staff", "Can manage company staff")` to `User.Meta.permissions`.

2.  **No Programmatic Assignment:** While Groups are created for each Role, permissions are not assigned to these groups in the code.
    - *Action Required:* Create a management command or data fixture to map the permissions listed above to their respective Groups (e.g., Assign `manage_members` to `HR_ADMIN` group).
