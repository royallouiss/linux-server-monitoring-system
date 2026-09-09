from unittest.mock import patch

from django.test import TestCase

from linux_server_monitoring_system.monitoring.jobs.monitoring import (
    MonitoringJob,
)
from linux_server_monitoring_system.servers.models import Server


class ServerHealthTests(TestCase):
    def create_server(self):
        return Server.objects.create(
            server_name="Test Server",
            hostname="192.168.1.100",
            username="testuser",
            password="testpassword",
        )

    def test_new_server_has_unknown_status(self):
        server = self.create_server()

        self.assertEqual(server.status, "UNKNOWN")
        self.assertIsNone(server.last_check_at)
        self.assertIsNone(server.last_success_at)
        self.assertEqual(server.last_error, "")

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_successful_monitoring_persists_server_health(
        self,
        mock_monitoring_service,
    ):
        server = self.create_server()

        service = mock_monitoring_service.for_server.return_value

        MonitoringJob.run(server)

        service.collect.assert_called_once_with()

        server.refresh_from_db()

        self.assertEqual(server.status, "UP")
        self.assertIsNotNone(server.last_check_at)
        self.assertIsNotNone(server.last_success_at)
        self.assertEqual(server.last_error, "")

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_failed_monitoring_persists_server_health(
        self,
        mock_monitoring_service,
    ):
        server = self.create_server()

        mock_monitoring_service.for_server.side_effect = RuntimeError(
            "SSH connection failed."
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "SSH connection failed.",
        ):
            MonitoringJob.run(server)

        server.refresh_from_db()

        self.assertEqual(server.status, "DOWN")
        self.assertIsNotNone(server.last_check_at)
        self.assertIsNone(server.last_success_at)
        self.assertEqual(
            server.last_error,
            "SSH connection failed.",
        )