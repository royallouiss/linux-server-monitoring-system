from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


def ensure_default_groups() -> dict[str, Group]:
    """Ensure standard system groups exist in the database.

    Graceful fallback so the system never fails if initial migration
    commands were not executed yet.
    """
    admin_group, _ = Group.objects.get_or_create(name="Admin")
    operator_group, _ = Group.objects.get_or_create(name="Operator")
    viewer_group, _ = Group.objects.get_or_create(name="Viewer")
    return {
        "Admin": admin_group,
        "Operator": operator_group,
        "Viewer": viewer_group,
    }


class IsAdminRole(BasePermission):
    """Allows access only to users with the Admin role or superusers.

    Admin privileges:
    - Add, edit, delete servers
    - Configure alerts
    - View monitoring & dashboards
    """

    message = "You must have Admin privileges to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_admin_role", False),
        )


class IsOperatorRole(BasePermission):
    """Allows access to users with Operator or Admin roles.

    Operator privileges:
    - Add and edit servers
    - View monitoring, alerts, and dashboards
    """

    message = "You must have Operator or Admin privileges to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_operator_role", False),
        )


class IsViewerRole(BasePermission):
    """Allows access to all authenticated users with Viewer role or higher.

    Viewer privileges:
    - View dashboard
    - View metrics
    - View alerts
    """

    message = "You must be logged in with at least Viewer privileges."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_viewer_role", False),
        )
