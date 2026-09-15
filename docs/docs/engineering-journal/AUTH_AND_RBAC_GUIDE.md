# Linux Server Monitoring System

## Authentication & Role-Based Access Control (RBAC) Guide

This document explains the authentication architecture, user roles, permission hierarchy, and usage instructions implemented for **Member 4 (Authentication + Deployment + QA)**.

---

# System Roles & Responsibilities

The system defines three distinct user roles:

| Role | Responsibility | Access Scope | Login Location |
|---|---|---|---|
| **Admin** | Full system control & infrastructure governance | Add, edit, delete servers; configure alerts; manage users | `/admin/` |
| **Operator** | Day-to-day server operations & monitoring | Add and edit servers; view monitoring metrics; view alerts | `/admin/` |
| **Viewer** | Read-only observation & audit | View dashboard, view metrics, view alerts | `/accounts/login/` |

---

# Role Permission Matrix

| Operation | Admin | Operator | Viewer |
|---|:---:|:---:|:---:|
| **View Dashboard** | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Metrics** | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Alerts** | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Monitoring** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Add Server** | ✅ Yes | ✅ Yes | ❌ Blocked |
| **Edit Server Details / SSH** | ✅ Yes | ✅ Yes | ❌ Blocked |
| **Delete Server** | ✅ **Yes** | ❌ Blocked | ❌ Blocked |
| **Configure Alert Thresholds** | ✅ **Yes** | ❌ Blocked | ❌ Blocked |
| **Manage Users & Assign Roles**| ✅ **Yes** | ❌ Blocked | ❌ Blocked |
| **Access Admin Panel (`/admin/`)**| ✅ Full Access | ⚠️ Restricted | ❌ Blocked |

---

# Initial Setup & Commands

### 1. Apply Database Migrations
Applies the `role` field to the PostgreSQL database:

```bash
uv run python manage.py migrate
```

---

### 2. Configure System Roles & Permissions
Automatically creates the `Admin`, `Operator`, and `Viewer` Django Groups and assigns model permissions:

```bash
uv run python manage.py setup_roles
```

---

### 3. Seed Demo Presentation Users
Creates three pre-configured accounts for testing and presentation:

```bash
uv run python manage.py seed_demo
```

### Pre-configured Demo Credentials:

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@example.com` | `AdminDemoPassword123!` |
| **Operator** | `operator@example.com` | `OperatorDemoPassword123!` |
| **Viewer** | `viewer@example.com` | `ViewerDemoPassword123!` |

---

# Developer Integration Guide

Team members can easily enforce role permissions in their respective modules.

### For API Developers (DRF Permissions):
Import permission classes from `users.permissions`:

```python
from rest_framework.views import APIView
from linux_server_monitoring_system.users.permissions import IsAdminRole, IsOperatorRole, IsViewerRole

# View that only Admins can access (e.g., delete server, configure alerts)
class DeleteServerAPIView(APIView):
    permission_classes = [IsAdminRole]
    ...

# View that Operators and Admins can access (e.g., add or edit server)
class ManageServerAPIView(APIView):
    permission_classes = [IsOperatorRole]
    ...

# View that Viewers, Operators, and Admins can access (e.g., fetch metrics)
class MetricsAPIView(APIView):
    permission_classes = [IsViewerRole]
    ...
```

---

### For Dashboard & Template Developers:
Use granular capability properties directly in HTML templates:

```html
<!-- Only Admins can see the Delete button -->
{% if request.user.can_delete_server %}
    <button class="btn btn-danger">Delete Server</button>
{% endif %}

<!-- Only Admins can see Configure Alerts link -->
{% if request.user.can_configure_alerts %}
    <a href="/alerts/settings/">Configure Alert Rules</a>
{% endif %}

<!-- All authenticated users (Admin, Operator, Viewer) can see Dashboard -->
{% if request.user.can_view_dashboard %}
    <div class="metrics-card">...</div>
{% endif %}
```

---

### For Web Views (Mixins & Decorators):
Import from `users.mixins`:

```python
from linux_server_monitoring_system.users.mixins import RoleRequiredMixin, role_required

# Class-Based View protection
class ServerManagementView(RoleRequiredMixin, TemplateView):
    allowed_roles = ["ADMIN", "OPERATOR"]
    template_name = "servers/manage.html"

# Function-Based View protection
@role_required(["ADMIN"])
def configure_alerts_view(request):
    ...
```

---

# Automated Testing

To run the RBAC test suite:

```bash
uv run pytest linux_server_monitoring_system/users/tests/test_rbac.py -v
```

All 14 test cases verify:
- Role assignment and safe defaults.
- Role hierarchy (`Admin > Operator > Viewer`).
- DRF permission classes.
- Web view decorators and mixins.
- Granular capability checks (`can_add_server`, `can_delete_server`, etc.).
