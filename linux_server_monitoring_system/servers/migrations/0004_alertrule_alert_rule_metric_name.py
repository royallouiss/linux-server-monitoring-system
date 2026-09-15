from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0003_alert"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlertRule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "metric_name",
                    models.CharField(
                        help_text="Metric name, or server_status for availability rules.",
                        max_length=255,
                    ),
                ),
                (
                    "operator",
                    models.CharField(
                        choices=[
                            (">", "Greater than"),
                            (">=", "Greater than or equal to"),
                            ("<", "Less than"),
                            ("<=", "Less than or equal to"),
                            ("=", "Equal to"),
                            ("!=", "Not equal to"),
                        ],
                        max_length=2,
                    ),
                ),
                (
                    "threshold",
                    models.CharField(
                        help_text="Numeric threshold or a server status such as DOWN.",
                        max_length=50,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("INFO", "Info"),
                            ("WARNING", "Warning"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="WARNING",
                        max_length=20,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                (
                    "server",
                    models.ForeignKey(
                        blank=True,
                        help_text="Leave empty to apply this rule to every server.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alert_rules",
                        to="servers.server",
                    ),
                ),
            ],
            options={
                "ordering": ["metric_name", "id"],
            },
        ),
        migrations.AddField(
            model_name="alert",
            name="metric_name",
            field=models.CharField(
                blank=True,
                help_text="The metric evaluated when this alert was generated.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="rule",
            field=models.ForeignKey(
                blank=True,
                help_text="The rule that generated this alert, when applicable.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alerts",
                to="servers.alertrule",
            ),
        ),
        migrations.AddConstraint(
            model_name="alertrule",
            constraint=models.UniqueConstraint(
                fields=("server", "metric_name", "operator", "threshold"),
                name="unique_alert_rule_scope",
            ),
        ),
    ]
