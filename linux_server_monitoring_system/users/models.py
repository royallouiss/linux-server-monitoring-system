
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """Default custom user model for Linux Server Monitoring & Management System.

    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("Admin")
        OPERATOR = "OPERATOR", _("Operator")
        VIEWER = "VIEWER", _("Viewer")

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text=_(
            "User role determining system permissions (Admin, Operator, Viewer).",
        ),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    @property
    def is_admin_role(self) -> bool:
        """Admin has full access (servers CRUD, alerts, monitoring)."""
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_operator_role(self) -> bool:
        """Operator has operational access (manage servers, view monitoring)."""
        return self.is_superuser or self.role in [self.Role.ADMIN, self.Role.OPERATOR]

    @property
    def is_viewer_role(self) -> bool:
        """Viewer has read-only access (view dashboard, metrics, alerts)."""
        return True

    def has_role_permission(self, required_role: str) -> bool:
        """Check if user role meets or exceeds the required privilege level."""
        if self.is_superuser:
            return True
        role_hierarchy = {
            self.Role.VIEWER: 1,
            self.Role.OPERATOR: 2,
            self.Role.ADMIN: 3,
        }
        user_level = role_hierarchy.get(self.role, 1)
        required_level = role_hierarchy.get(required_role, 1)
        return user_level >= required_level

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

