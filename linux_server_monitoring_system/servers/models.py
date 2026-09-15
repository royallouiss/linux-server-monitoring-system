from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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

    def __str__(self):
        return self.server_name


class Alert(models.Model):
    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    rule = models.ForeignKey(
        "AlertRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="The rule that generated this alert, when applicable.",
    )
    metric_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The metric evaluated when this alert was generated.",
    )

    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="The server associated with this alert.",
    )
    title = models.CharField(
        max_length=200,
        help_text="Summary of the alert issue.",
    )
    message = models.TextField(
        blank=True,
        help_text="Detailed alert description or diagnostic log.",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.WARNING,
        help_text="Severity level of the alert.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current state of the alert.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the alert was marked resolved.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.server.server_name}: {self.title}"

    def resolve(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])


class AlertRule(models.Model):
    class Operator(models.TextChoices):
        GREATER_THAN = ">", "Greater than"
        GREATER_THAN_OR_EQUAL = ">=", "Greater than or equal to"
        LESS_THAN = "<", "Less than"
        LESS_THAN_OR_EQUAL = "<=", "Less than or equal to"
        EQUAL = "=", "Equal to"
        NOT_EQUAL = "!=", "Not equal to"

    metric_name = models.CharField(
        max_length=255,
        help_text="Metric name, or server_status for availability rules.",
    )
    operator = models.CharField(
        max_length=2,
        choices=Operator.choices,
    )
    threshold = models.CharField(
        max_length=50,
        help_text="Numeric threshold or a server status such as DOWN.",
    )
    severity = models.CharField(
        max_length=20,
        choices=Alert.Severity.choices,
        default=Alert.Severity.WARNING,
    )
    enabled = models.BooleanField(default=True)
    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alert_rules",
        help_text="Leave empty to apply this rule to every server.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["server", "metric_name", "operator", "threshold"],
                name="unique_alert_rule_scope",
            ),
        ]
        ordering = ["metric_name", "id"]

    def __str__(self):
        scope = self.server.server_name if self.server else "all servers"
        return f"{self.metric_name} {self.operator} {self.threshold} ({scope})"
