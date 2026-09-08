from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.jobs.monitoring import (
    MonitoringJob,
)


class MonitoringJobTests(SimpleTestCase):
    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_runs_monitoring_for_server(self, mock_monitoring_service):
        server = Mock()
        service = Mock()

        mock_monitoring_service.for_server.return_value = service

        MonitoringJob.run(server)

        mock_monitoring_service.for_server.assert_called_once_with(
            server
        )

        service.collect.assert_called_once_with()

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_propagates_monitoring_service_failure(
        self,
        mock_monitoring_service,
    ):
        server = Mock()

        mock_monitoring_service.for_server.side_effect = RuntimeError(
            "Monitoring failed."
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Monitoring failed.",
        ):
            MonitoringJob.run(server)

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_marks_server_up_when_monitoring_succeeds(
        self,
        mock_monitoring_service,
    ):
        server = Mock()
        service = Mock()

        mock_monitoring_service.for_server.return_value = service

        MonitoringJob.run(server)

        self.assertEqual(server.status, "UP")
        self.assertIsNotNone(server.last_check_at)
        self.assertIsNotNone(server.last_success_at)
        self.assertEqual(server.last_error, "")

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_marks_server_down_when_monitoring_fails(
        self,
        mock_monitoring_service,
    ):
        server = Mock()

        previous_success = datetime(
            2026,
            9,
            8,
            17,
            30,
            tzinfo=timezone.utc,
        )

        server.last_success_at = previous_success

        mock_monitoring_service.for_server.side_effect = RuntimeError(
            "SSH connection failed."
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "SSH connection failed.",
        ):
            MonitoringJob.run(server)

        self.assertEqual(server.status, "DOWN")
        self.assertIsNotNone(server.last_check_at)
        self.assertEqual(
            server.last_success_at,
            previous_success,
        )
        self.assertEqual(
            server.last_error,
            "SSH connection failed.",
        )