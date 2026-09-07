from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.monitoring.services.monitoring import (
    MonitoringService,
)
from linux_server_monitoring_system.servers.models import Server


class MonitoringServiceTests(TestCase):

    def test_collects_and_stores_metrics(self):
        server = Server.objects.create(
            server_name="SAN Ubuntu",
            hostname="192.168.1.8",
            ssh_port=22,
            username="sandra",
            password="test-password",
        )

        class FakeCPUCollector:
            def collect(self):
                return {
                    "logical_cpus": 8,
                    "usage_percent": 12.5,
                    "load_average": {
                        "1m": 0.15,
                        "5m": 0.05,
                        "15m": 0.01,
                    },
                }

        class FakeMemoryCollector:
            def collect(self):
                return {
                    "memory": {
                        "total_bytes": 4000000000,
                        "used_bytes": 1000000000,
                        "available_bytes": 3000000000,
                        "usage_percent": 25.0,
                    },
                    "swap": {
                        "total_bytes": 1000000000,
                        "used_bytes": 100000000,
                        "usage_percent": 10.0,
                    },
                }

        class FakeDiskCollector:
            def collect(self):
                return {
                    "/": {
                        "total_bytes": 100000000000,
                        "used_bytes": 60000000000,
                        "available_bytes": 40000000000,
                        "usage_percent": 60.0,
                    },
                }

        timestamp = timezone.make_aware(
            datetime(2026, 8, 31, 9, 45, 0)
        )

        service = MonitoringService(
            server=server,
            cpu_collector=FakeCPUCollector(),
            memory_collector=FakeMemoryCollector(),
            disk_collector=FakeDiskCollector(),
        )

        service.collect(timestamp=timestamp)

        samples = MetricSample.objects.filter(
            server=server,
        ).order_by("metric_name")

        self.assertEqual(samples.count(), 11)

        # CPU metrics

        cpu_usage = samples.get(metric_name="cpu_usage")
        self.assertEqual(cpu_usage.value, Decimal("12.500000"))
        self.assertEqual(cpu_usage.unit, "percent")
        self.assertEqual(cpu_usage.timestamp, timestamp)

        load_1m = samples.get(metric_name="load_1m")
        self.assertEqual(load_1m.value, Decimal("0.150000"))
        self.assertEqual(load_1m.unit, "load")

        load_5m = samples.get(metric_name="load_5m")
        self.assertEqual(load_5m.value, Decimal("0.050000"))
        self.assertEqual(load_5m.unit, "load")

        load_15m = samples.get(metric_name="load_15m")
        self.assertEqual(load_15m.value, Decimal("0.010000"))
        self.assertEqual(load_15m.unit, "load")

        # Memory metrics

        memory_used = samples.get(metric_name="memory_used")
        self.assertEqual(
            memory_used.value,
            Decimal("1000000000"),
        )
        self.assertEqual(memory_used.unit, "bytes")

        memory_available = samples.get(
            metric_name="memory_available"
        )
        self.assertEqual(
            memory_available.value,
            Decimal("3000000000"),
        )
        self.assertEqual(memory_available.unit, "bytes")

        memory_usage = samples.get(
            metric_name="memory_usage"
        )
        self.assertEqual(
            memory_usage.value,
            Decimal("25.000000"),
        )
        self.assertEqual(memory_usage.unit, "percent")

        swap_usage = samples.get(
            metric_name="swap_usage"
        )
        self.assertEqual(
            swap_usage.value,
            Decimal("10.000000"),
        )
        self.assertEqual(swap_usage.unit, "percent")

        # Disk metrics - root filesystem

        root_used = samples.get(
            metric_name="disk_used:/"
        )
        self.assertEqual(
            root_used.value,
            Decimal("60000000000"),
        )
        self.assertEqual(root_used.unit, "bytes")
        self.assertEqual(root_used.timestamp, timestamp)

        root_available = samples.get(
            metric_name="disk_available:/"
        )
        self.assertEqual(
            root_available.value,
            Decimal("40000000000"),
        )
        self.assertEqual(root_available.unit, "bytes")

        root_usage = samples.get(
            metric_name="disk_usage:/"
        )
        self.assertEqual(
            root_usage.value,
            Decimal("60.000000"),
        )
        self.assertEqual(root_usage.unit, "percent")

    def test_collect_rolls_back_when_storage_fails(self):
        server = Server.objects.create(
            server_name="SAN Ubuntu",
            hostname="192.168.1.8",
            ssh_port=22,
            username="sandra",
            password="test-password",
        )

        class FakeCPUCollector:
            def collect(self):
                return {
                    "logical_cpus": 8,
                    "usage_percent": 12.5,
                    "load_average": {
                        "1m": 0.15,
                        "5m": 0.05,
                        "15m": 0.01,
                    },
                }

        class FailingMemoryCollector:
            def collect(self):
                raise RuntimeError("Memory collection failed.")

        class FakeDiskCollector:
            def collect(self):
                return {
                    "/": {
                        "total_bytes": 100000000000,
                        "used_bytes": 60000000000,
                        "available_bytes": 40000000000,
                        "usage_percent": 60.0,
                    },
                }

        service = MonitoringService(
            server=server,
            cpu_collector=FakeCPUCollector(),
            memory_collector=FailingMemoryCollector(),
            disk_collector=FakeDiskCollector(),
        )

        with self.assertRaises(RuntimeError):
            service.collect()

        self.assertEqual(
            MetricSample.objects.filter(server=server).count(),
            0,
        )

    @patch(
        "linux_server_monitoring_system.monitoring.services.monitoring.SSHService"
    )
    def test_creates_service_for_server(self, mock_ssh_service):
        server = Server.objects.create(
            server_name="SAN Ubuntu",
            hostname="192.168.1.8",
            ssh_port=22,
            username="sandra",
            password="test-password",
        )

        mock_ssh_service.return_value.connect.return_value = (
            True,
            "Connection successful.",
        )

        service = MonitoringService.for_server(server)

        self.assertEqual(service.server, server)
        self.assertIsNotNone(service.cpu_collector)
        self.assertIsNotNone(service.memory_collector)
        self.assertIsNotNone(service.disk_collector)

        mock_ssh_service.return_value.connect.assert_called_once_with(
            hostname="192.168.1.8",
            port=22,
            username="sandra",
            password="test-password",
        )

    @patch(
        "linux_server_monitoring_system.monitoring.services.monitoring.SSHService"
    )
    def test_for_server_raises_when_ssh_connection_fails(
        self,
        mock_ssh_service,
    ):
        server = Server.objects.create(
            server_name="SAN Ubuntu",
            hostname="192.168.1.8",
            ssh_port=22,
            username="sandra",
            password="test-password",
        )

        mock_ssh_service.return_value.connect.return_value = (
            False,
            "Authentication failed.",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Authentication failed.",
        ):
            MonitoringService.for_server(server)