from unittest.mock import patch

from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.schedulers.monitoring import (
    MonitoringScheduler,
)


class MonitoringSchedulerTests(SimpleTestCase):
    @patch(
        "linux_server_monitoring_system.monitoring.schedulers.monitoring.MonitoringRunner"
    )
    def test_runs_monitoring_for_active_servers(
        self,
        mock_monitoring_runner,
    ):
        server_1 = object()
        server_2 = object()

        mock_monitoring_runner.run.return_value = {
            "successful": [server_1, server_2],
            "failed": [],
        }

        with patch(
            "linux_server_monitoring_system.monitoring.schedulers.monitoring.Server"
        ) as mock_server:
            (
                mock_server.objects.filter.return_value
            ) = [server_1, server_2]

            result = MonitoringScheduler.run()

        mock_server.objects.filter.assert_called_once_with(
            is_active=True,
        )

        mock_monitoring_runner.run.assert_called_once_with(
            [server_1, server_2],
        )

        self.assertEqual(
            result,
            {
                "successful": [server_1, server_2],
                "failed": [],
            },
        )