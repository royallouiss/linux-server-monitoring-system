from django.db import models

from linux_server_monitoring_system.servers.models import Server


class MetricSample(models.Model):
    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE,
        related_name="metric_samples",
    )

    metric_name = models.CharField(
        max_length=50,
    )

    value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    unit = models.CharField(
        max_length=20,
    )

    timestamp = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=["server", "metric_name", "timestamp"],
            ),
        ]

    def __str__(self):
        return f"{self.server.server_name} - {self.metric_name}"