from __future__ import annotations

from typing import Any

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand

from linux_server_monitoring_system.users.models import User


class Command(BaseCommand):
    help = (
        "Seeds presentation demo users (Admin, Operator, Viewer) with secure defaults."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.NOTICE("Seeding demo presentation users..."))

        # Setup standard roles & permissions
        call_command("setup_roles")

        demo_users = [
            {
                "email": "admin@example.com",
                "name": "System Administrator",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": False,
                "password": "AdminDemoPassword123!",
                "group_name": "Admin",
            },
            {
                "email": "operator@example.com",
                "name": "DevOps Operator",
                "role": User.Role.OPERATOR,
                "is_staff": True,
                "is_superuser": False,
                "password": "OperatorDemoPassword123!",
                "group_name": "Operator",
            },
            {
                "email": "viewer@example.com",
                "name": "Metrics Viewer",
                "role": User.Role.VIEWER,
                "is_staff": False,
                "is_superuser": False,
                "password": "ViewerDemoPassword123!",
                "group_name": "Viewer",
            },
        ]

        for user_data in demo_users:
            user, created = User.objects.get_or_create(
                email=user_data["email"],
                defaults={
                    "name": user_data["name"],
                    "role": user_data["role"],
                    "is_staff": user_data["is_staff"],
                    "is_superuser": user_data["is_superuser"],
                },
            )

            # Ensure role and staff attributes are current
            user.role = user_data["role"]
            user.is_staff = user_data["is_staff"]
            user.set_password(user_data["password"])
            user.save()

            group = Group.objects.filter(name=user_data["group_name"]).first()
            if group:
                user.groups.add(group)

            # Ensure email is verified in allauth
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"verified": True, "primary": True},
            )

            action_label = "Created" if created else "Updated"
            name = user_data["name"]
            email = user_data["email"]
            role = user_data["role"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [{action_label}] {name} ({email}) -> Role: {role}",
                ),
            )

        self.stdout.write(self.style.SUCCESS("\nDemo users successfully seeded!"))
        self.stdout.write("Credentials:")
        self.stdout.write(
            "  Admin:    admin@example.com    | Password: AdminDemoPassword123!",
        )
        self.stdout.write(
            "  Operator: operator@example.com | Password: OperatorDemoPassword123!",
        )
        self.stdout.write(
            "  Viewer:   viewer@example.com   | Password: ViewerDemoPassword123!",
        )
