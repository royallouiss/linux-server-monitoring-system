from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from linux_server_monitoring_system.servers.models import Server
from linux_server_monitoring_system.users.models import User


class Command(BaseCommand):
    help = "Initializes system roles (Admin, Operator, Viewer) and assigns permissions."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(
            self.style.NOTICE("Setting up system roles and permissions..."),
        )

        # 1. Ensure Groups Exist
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        operator_group, _ = Group.objects.get_or_create(name="Operator")
        viewer_group, _ = Group.objects.get_or_create(name="Viewer")

        # 2. Get Permissions for Server and User models
        server_ct = ContentType.objects.get_for_model(Server)
        user_ct = ContentType.objects.get_for_model(User)

        all_server_perms = Permission.objects.filter(content_type=server_ct)
        view_server_perm = Permission.objects.filter(
            content_type=server_ct,
            codename__startswith="view_",
        )
        change_server_perms = Permission.objects.filter(
            content_type=server_ct,
            codename__in=["view_server", "add_server", "change_server"],
        )

        all_user_perms = Permission.objects.filter(content_type=user_ct)
        view_user_perm = Permission.objects.filter(
            content_type=user_ct,
            codename__startswith="view_",
        )

        # Admin: Full control over Servers and Users
        admin_group.permissions.set(list(all_server_perms) + list(all_user_perms))

        # Operator: Add/Change/View servers, view users
        operator_group.permissions.set(list(change_server_perms) + list(view_user_perm))

        # Viewer: Read-only access to servers and users
        viewer_group.permissions.set(list(view_server_perm) + list(view_user_perm))

        self.stdout.write(self.style.SUCCESS("System roles configured successfully:"))
        self.stdout.write("  - Admin Group: Full management & configuration")
        self.stdout.write(
            "  - Operator Group: Operational server management & monitoring",
        )
        self.stdout.write("  - Viewer Group: Read-only viewing permissions")
