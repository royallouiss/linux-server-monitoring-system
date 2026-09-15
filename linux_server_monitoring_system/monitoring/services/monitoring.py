from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from linux_server_monitoring_system.core.ssh import SSHService
from linux_server_monitoring_system.monitoring.collectors.cpu import CPUCollector
from linux_server_monitoring_system.monitoring.collectors.disk import DiskCollector
from linux_server_monitoring_system.monitoring.collectors.memory import MemoryCollector
from linux_server_monitoring_system.monitoring.collectors.network import NetworkCollector
from linux_server_monitoring_system.monitoring.models import MetricSample


class MonitoringService:
    def __init__(
        self,
        server,
        cpu_collector,
        memory_collector,
        disk_collector,
        network_collector,
    ):
        self.server = server
        self.cpu_collector = cpu_collector
        self.memory_collector = memory_collector
        self.disk_collector = disk_collector
        self.network_collector = network_collector

    @transaction.atomic
    def collect(self, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()

        cpu_metrics = self.cpu_collector.collect()
        memory_metrics = self.memory_collector.collect()
        disk_metrics = self.disk_collector.collect()
        network_metrics = self.network_collector.collect()

        self._store_cpu_metrics(cpu_metrics, timestamp)
        self._store_memory_metrics(memory_metrics, timestamp)
        self._store_disk_metrics(disk_metrics, timestamp)
        self._store_network_metrics(network_metrics, timestamp)

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

    def _store_disk_metrics(self, metrics, timestamp):
        samples = []

        for mount_point, disk in metrics.items():
            samples.extend(
                [
                    MetricSample(
                        server=self.server,
                        metric_name=f"disk_used:{mount_point}",
                        value=Decimal(str(disk["used_bytes"])),
                        unit="bytes",
                        timestamp=timestamp,
                    ),
                    MetricSample(
                        server=self.server,
                        metric_name=f"disk_available:{mount_point}",
                        value=Decimal(str(disk["available_bytes"])),
                        unit="bytes",
                        timestamp=timestamp,
                    ),
                    MetricSample(
                        server=self.server,
                        metric_name=f"disk_usage:{mount_point}",
                        value=Decimal(str(disk["usage_percent"])),
                        unit="percent",
                        timestamp=timestamp,
                    ),
                ]
            )

        MetricSample.objects.bulk_create(samples)

    def _store_network_metrics(self, metrics, timestamp):
        samples = []

        for interface, network in metrics.items():
            samples.extend(
                [
                    MetricSample(
                        server=self.server,
                        metric_name=f"network_received_bytes:{interface}",
                        value=Decimal(
                            str(network["received_bytes"])
                        ),
                        unit="bytes",
                        timestamp=timestamp,
                    ),
                    MetricSample(
                        server=self.server,
                        metric_name=f"network_transmitted_bytes:{interface}",
                        value=Decimal(
                            str(network["transmitted_bytes"])
                        ),
                        unit="bytes",
                        timestamp=timestamp,
                    ),
                    MetricSample(
                        server=self.server,
                        metric_name=f"network_receive_rate:{interface}",
                        value=Decimal(
                            str(network["receive_rate"])
                        ),
                        unit="bytes_per_second",
                        timestamp=timestamp,
                    ),
                    MetricSample(
                        server=self.server,
                        metric_name=f"network_transmit_rate:{interface}",
                        value=Decimal(
                            str(network["transmit_rate"])
                        ),
                        unit="bytes_per_second",
                        timestamp=timestamp,
                    ),
                ]
            )

        MetricSample.objects.bulk_create(samples)

    @classmethod
    def for_server(cls, server):
        ssh = SSHService()

        success, message = ssh.connect(
            hostname=server.hostname,
            port=server.ssh_port,
            username=server.username,
            password=server.password,
        )

        if not success:
            raise RuntimeError(message)

        return cls(
            server=server,
            cpu_collector=CPUCollector(ssh),
            memory_collector=MemoryCollector(ssh),
            disk_collector=DiskCollector(ssh),
            network_collector=NetworkCollector(ssh),
        )