from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING
from typing import Any

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest
    from django.http import HttpResponse


class RolePermissionDenied(PermissionDenied):
    """Custom exception raised when user lacks required role permissions."""

    default_message = "You do not have the required role to access this resource."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin for Class-Based Views that enforces minimum role requirements.

    Example:
        class ServerCreateView(RoleRequiredMixin, CreateView):
            allowed_roles = ["ADMIN", "OPERATOR"]
    """

    allowed_roles: list[str] = ["ADMIN"]

    def test_func(self) -> bool:
        user = self.request.user  # type: ignore[attr-defined]
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        user_role = getattr(user, "role", "")
        return user_role in self.allowed_roles

    def handle_no_permission(self) -> HttpResponse:
        if not self.request.user.is_authenticated:  # type: ignore[attr-defined]
            return super().handle_no_permission()
        raise RolePermissionDenied


def role_required(allowed_roles: list[str] | None = None) -> Callable[..., Any]:
    """Decorator for function-based views to enforce role access control.

    Example:
        @role_required(["ADMIN"])
        def my_view(request):
            ...
    """
    effective_roles = allowed_roles if allowed_roles is not None else ["ADMIN"]

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped_view(
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = getattr(request.user, "role", "")
            if user_role not in effective_roles:
                raise RolePermissionDenied

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
