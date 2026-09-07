from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from rest_framework.views import APIView

from linux_server_monitoring_system.users.mixins import RoleRequiredMixin
from linux_server_monitoring_system.users.mixins import role_required
from linux_server_monitoring_system.users.models import User
from linux_server_monitoring_system.users.permissions import IsAdminRole
from linux_server_monitoring_system.users.permissions import IsOperatorRole
from linux_server_monitoring_system.users.permissions import IsViewerRole
from linux_server_monitoring_system.users.permissions import ensure_default_groups


@pytest.mark.django_db
class TestUserRoles:
    def test_default_role_is_viewer(self):
        user = User.objects.create(email="test_viewer@example.com")
        assert user.role == User.Role.VIEWER
        assert user.is_viewer_role is True
        assert user.is_operator_role is False
        assert user.is_admin_role is False

    def test_operator_role_properties(self):
        user = User.objects.create(
            email="test_operator@example.com",
            role=User.Role.OPERATOR,
        )
        assert user.is_viewer_role is True
        assert user.is_operator_role is True
        assert user.is_admin_role is False

    def test_admin_role_properties(self):
        user = User.objects.create(
            email="test_admin@example.com",
            role=User.Role.ADMIN,
        )
        assert user.is_viewer_role is True
        assert user.is_operator_role is True
        assert user.is_admin_role is True

    def test_superuser_has_all_roles(self):
        user = User.objects.create(
            email="test_super@example.com",
            role=User.Role.VIEWER,
            is_superuser=True,
        )
        assert user.is_viewer_role is True
        assert user.is_operator_role is True
        assert user.is_admin_role is True
        assert user.has_role_permission(User.Role.ADMIN) is True

    def test_role_hierarchy(self):
        viewer = User.objects.create(
            email="h_viewer@example.com",
            role=User.Role.VIEWER,
        )
        operator = User.objects.create(
            email="h_operator@example.com",
            role=User.Role.OPERATOR,
        )
        admin = User.objects.create(
            email="h_admin@example.com",
            role=User.Role.ADMIN,
        )

        assert viewer.has_role_permission(User.Role.VIEWER) is True
        assert viewer.has_role_permission(User.Role.OPERATOR) is False
        assert viewer.has_role_permission(User.Role.ADMIN) is False

        assert operator.has_role_permission(User.Role.VIEWER) is True
        assert operator.has_role_permission(User.Role.OPERATOR) is True
        assert operator.has_role_permission(User.Role.ADMIN) is False

        assert admin.has_role_permission(User.Role.VIEWER) is True
        assert admin.has_role_permission(User.Role.OPERATOR) is True
        assert admin.has_role_permission(User.Role.ADMIN) is True


@pytest.mark.django_db
class TestDRFPermissions:
    def setup_method(self):
        self.factory = RequestFactory()
        self.view = APIView()
        self.admin_user = User.objects.create(
            email="p_admin@example.com",
            role=User.Role.ADMIN,
        )
        self.operator_user = User.objects.create(
            email="p_operator@example.com",
            role=User.Role.OPERATOR,
        )
        self.viewer_user = User.objects.create(
            email="p_viewer@example.com",
            role=User.Role.VIEWER,
        )

    def test_is_admin_permission(self):
        perm = IsAdminRole()
        request = self.factory.get("/")

        request.user = self.admin_user
        assert perm.has_permission(request, self.view) is True

        request.user = self.operator_user
        assert perm.has_permission(request, self.view) is False

        request.user = self.viewer_user
        assert perm.has_permission(request, self.view) is False

        request.user = AnonymousUser()
        assert perm.has_permission(request, self.view) is False

    def test_is_operator_permission(self):
        perm = IsOperatorRole()
        request = self.factory.get("/")

        request.user = self.admin_user
        assert perm.has_permission(request, self.view) is True

        request.user = self.operator_user
        assert perm.has_permission(request, self.view) is True

        request.user = self.viewer_user
        assert perm.has_permission(request, self.view) is False

    def test_is_viewer_permission(self):
        perm = IsViewerRole()
        request = self.factory.get("/")

        request.user = self.admin_user
        assert perm.has_permission(request, self.view) is True

        request.user = self.operator_user
        assert perm.has_permission(request, self.view) is True

        request.user = self.viewer_user
        assert perm.has_permission(request, self.view) is True

        request.user = AnonymousUser()
        assert perm.has_permission(request, self.view) is False

    def test_ensure_default_groups_fallback(self):
        groups = ensure_default_groups()
        assert "Admin" in groups
        assert "Operator" in groups
        assert "Viewer" in groups


@pytest.mark.django_db
class TestViewMixinsAndDecorators:
    def setup_method(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create(
            email="v_admin@example.com",
            role=User.Role.ADMIN,
        )
        self.viewer_user = User.objects.create(
            email="v_viewer@example.com",
            role=User.Role.VIEWER,
        )

    def test_role_required_decorator_allows_authorized_role(self):
        @role_required(["ADMIN"])
        def protected_view(request):
            return "access_granted"

        request = self.factory.get("/")
        request.user = self.admin_user
        assert protected_view(request) == "access_granted"

    def test_role_required_decorator_blocks_unauthorized_role(self):
        @role_required(["ADMIN"])
        def protected_view(request):
            return "access_granted"

        request = self.factory.get("/")
        request.user = self.viewer_user
        with pytest.raises(PermissionDenied):
            protected_view(request)

    def test_role_required_mixin(self):
        class DummyView(RoleRequiredMixin):
            allowed_roles = ["ADMIN"]

            def __init__(self, request):
                self.request = request

        request = self.factory.get("/")
        request.user = self.admin_user
        view = DummyView(request)
        assert view.test_func() is True

        request.user = self.viewer_user
        view_denied = DummyView(request)
        assert view_denied.test_func() is False
