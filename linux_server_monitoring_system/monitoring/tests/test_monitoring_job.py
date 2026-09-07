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