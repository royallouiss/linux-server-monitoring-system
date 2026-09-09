from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Server(models.Model):
    OPERATING_SYSTEM_CHOICES = [
        ("UBUNTU", "Ubuntu"),
        ("DEBIAN", "Debian"),
        ("CENTOS", "CentOS"),
        ("ROCKY", "Rocky Linux"),
        ("AMAZON", "Amazon Linux"),
    ]

    STATUS_CHOICES = [
        ("UNKNOWN", "Unknown"),
        ("UP", "Up"),
        ("DOWN", "Down"),
    ]

    server_name = models.CharField(
        max_length=100,
        help_text="Human-readable name of the server.",
    )

    hostname = models.CharField(
        max_length=255,
        unique=True,
        help_text="Hostname or IP address of the server.",
    )

    ssh_port = models.PositiveIntegerField(
        default=22,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(65535),
        ],
        help_text="SSH port number.",
    )

    username = models.CharField(
        max_length=100,
        help_text="Username used for SSH authentication.",
    )

    password = models.CharField(
        max_length=255,
        help_text="Password used for SSH authentication.",
    )

    operating_system = models.CharField(
        max_length=20,
        choices=OPERATING_SYSTEM_CHOICES,
        default="UBUNTU",
        help_text="Operating system running on the server.",
    )

    description = models.TextField(
        blank=True,
        help_text="Optional notes about the server.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether monitoring is enabled for this server.",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="UNKNOWN",
        help_text="Current monitoring status of the server.",
    )

    last_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When monitoring was last attempted.",
    )

    last_success_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When monitoring last succeeded.",
    )

    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Error from the latest failed monitoring attempt.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )