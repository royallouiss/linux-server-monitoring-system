from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from linux_server_monitoring_system.alerts.services.evaluator import AlertEvaluator
from linux_server_monitoring_system.alerts.services.notifications import (
    EmailNotificationService,
)
from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Alert
from linux_server_monitoring_system.servers.models import AlertRule
from linux_server_monitoring_system.servers.models import Server


class AlertEvaluatorTests(TestCase):
    def setUp(self):
        self.server = Server.objects.create(
            server_name="Test Server",
            hostname="192.168.1.100",
            username="testuser",
            password="testpassword",
        )
        self.rule = AlertRule.objects.create(
            metric_name="cpu_usage",
            operator=AlertRule.Operator.GREATER_THAN,
            threshold="80",
            severity=Alert.Severity.WARNING,
        )
        self.notification_service = RecordingNotificationService()
        self.evaluator = AlertEvaluator(self.notification_service)

    def add_sample(self, value):
        return MetricSample.objects.create(
            server=self.server,
            metric_name="cpu_usage",
            value=value,
            unit="percent",
            timestamp=timezone.now(),
        )

    def test_threshold_lifecycle_deduplicates_and_retriggers(self):
        self.add_sample(85)
        self.evaluator.evaluate_server(self.server)
        self.assertEqual(Alert.objects.filter(status=Alert.Status.ACTIVE).count(), 1)

        self.add_sample(90)
        self.evaluator.evaluate_server(self.server)
        self.assertEqual(Alert.objects.filter(status=Alert.Status.ACTIVE).count(), 1)
        self.assertEqual(len(self.notification_service.alerts), 1)

        self.add_sample(60)
        self.evaluator.evaluate_server(self.server)
        self.assertEqual(Alert.objects.filter(status=Alert.Status.RESOLVED).count(), 1)

        self.add_sample(95)
        self.evaluator.evaluate_server(self.server)
        self.assertEqual(Alert.objects.filter(status=Alert.Status.ACTIVE).count(), 1)
        self.assertEqual(Alert.objects.count(), 2)
        self.assertEqual(len(self.notification_service.alerts), 2)

    def test_server_down_alert_resolves_after_recovery(self):
        rule = AlertRule.objects.create(
            metric_name="server_status",
            operator=AlertRule.Operator.EQUAL,
            threshold="DOWN",
            severity=Alert.Severity.CRITICAL,
        )
        self.server.status = Server.STATUS_CHOICES[2][0]
        self.server.save(update_fields=["status"])

        self.evaluator.evaluate_server(self.server)
        alert = Alert.objects.get(rule=rule)
        self.assertEqual(alert.severity, Alert.Severity.CRITICAL)

        self.server.status = Server.STATUS_CHOICES[1][0]
        self.server.save(update_fields=["status"])
        self.evaluator.evaluate_server(self.server)
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.RESOLVED)

    def test_disabled_rule_does_not_create_alert(self):
        self.rule.enabled = False
        self.rule.save(update_fields=["enabled"])
        self.add_sample(95)

        self.evaluator.evaluate_server(self.server)

        self.assertFalse(Alert.objects.exists())

    def test_multiple_servers_are_evaluated_independently(self):
        other_server = Server.objects.create(
            server_name="Other Server",
            hostname="192.168.1.101",
            username="testuser",
            password="testpassword",
        )
        self.add_sample(95)
        MetricSample.objects.create(
            server=other_server,
            metric_name="cpu_usage",
            value=20,
            unit="percent",
            timestamp=timezone.now(),
        )

        self.evaluator.evaluate_server(self.server)
        self.evaluator.evaluate_server(other_server)

        self.assertEqual(Alert.objects.filter(server=self.server).count(), 1)
        self.assertFalse(Alert.objects.filter(server=other_server).exists())


class RecordingNotificationService:
    def __init__(self):
        self.alerts = []

    def notify(self, alert):
        self.alerts.append(alert)
        return True


class NotificationServiceTests(TestCase):
    @patch("linux_server_monitoring_system.alerts.services.notifications.send_mail")
    def test_email_notification_uses_configured_recipient(self, send_mail):
        server = Server.objects.create(
            server_name="Test Server",
            hostname="192.168.1.100",
            username="testuser",
            password="testpassword",
        )
        alert = Alert.objects.create(
            server=server,
            title="High CPU",
            message="CPU is high.",
        )

        service = EmailNotificationService(["ops@example.com"])
        service.notify(alert)

        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.kwargs["recipient_list"], ["ops@example.com"])
