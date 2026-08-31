from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from linux_server_monitoring_system.monitoring.models import MetricSample


class MonitoringService:
    def __init__(
        self,
        server,
        cpu_collector,
        memory_collector,
    ):
        self.server = server
        self.cpu_collector = cpu_collector
        self.memory_collector = memory_collector

    @transaction.atomic
    def collect(self, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()

        cpu_metrics = self.cpu_collector.collect()
        memory_metrics = self.memory_collector.collect()

        self._store_cpu_metrics(
            cpu_metrics,
            timestamp,
        )

        self._store_memory_metrics(
            memory_metrics,
            timestamp,
        )

    def _store_cpu_metrics(self, metrics, timestamp):
        MetricSample.objects.bulk_create(
            [
                MetricSample(
                    server=self.server,
                    metric_name="cpu_usage",
                    value=Decimal(str(metrics["usage_percent"])),
                    unit="percent",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="load_1m",
                    value=Decimal(str(metrics["load_average"]["1m"])),
                    unit="load",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="load_5m",
                    value=Decimal(str(metrics["load_average"]["5m"])),
                    unit="load",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="load_15m",
                    value=Decimal(str(metrics["load_average"]["15m"])),
                    unit="load",
                    timestamp=timestamp,
                ),
            ]
        )

    def _store_memory_metrics(self, metrics, timestamp):
        memory = metrics["memory"]
        swap = metrics["swap"]

        MetricSample.objects.bulk_create(
            [
                MetricSample(
                    server=self.server,
                    metric_name="memory_used",
                    value=Decimal(str(memory["used_bytes"])),
                    unit="bytes",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="memory_available",
                    value=Decimal(str(memory["available_bytes"])),
                    unit="bytes",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="memory_usage",
                    value=Decimal(str(memory["usage_percent"])),
                    unit="percent",
                    timestamp=timestamp,
                ),
                MetricSample(
                    server=self.server,
                    metric_name="swap_usage",
                    value=Decimal(str(swap["usage_percent"])),
                    unit="percent",
                    timestamp=timestamp,
                ),
            ]
        )