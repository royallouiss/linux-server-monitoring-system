from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Server


class MetricSampleTests(TestCase):
    def test_creates_metric_sample(self):
        server = Server.objects.create(
            server_name="SAN Ubuntu",
            hostname="192.168.1.8",
            ssh_port=22,
            username="sandra",
            password="test-password",
        )

        timestamp = timezone.make_aware(
            datetime(2026, 8, 31, 9, 45, 0)
        )

        sample = MetricSample.objects.create(
            server=server,
            metric_name="cpu_usage",
            value=12.345678,
            unit="percent",
            timestamp=timestamp,
        )

        self.assertEqual(sample.server, server)
        self.assertEqual(sample.metric_name, "cpu_usage")
        self.assertEqual(sample.value, 12.345678)
        self.assertEqual(sample.unit, "percent")
        self.assertEqual(sample.timestamp, timestamp)