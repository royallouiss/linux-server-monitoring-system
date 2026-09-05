from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class MonitoringCommandTests(SimpleTestCase):

    @patch(
        "linux_server_monitoring_system.monitoring.management.commands.monitor_servers.MonitoringScheduler"
    )
    def test_runs_monitoring_scheduler(
        self,
        mock_monitoring_scheduler,
    ):
        mock_monitoring_scheduler.run.return_value = {
            "successful": [object(), object()],
            "failed": [],
        }

        output = StringIO()

        call_command(
            "monitor_servers",
            stdout=output,
        )

        mock_monitoring_scheduler.run.assert_called_once_with()

        self.assertIn("Monitoring completed.", output.getvalue())
        self.assertIn("Successful servers: 2", output.getvalue())
        self.assertIn("Failed servers: 0", output.getvalue())

    @patch(
        "linux_server_monitoring_system.monitoring.management.commands.monitor_servers.MonitoringScheduler"
    )
    def test_reports_successful_and_failed_servers(
        self,
        mock_monitoring_scheduler,
    ):
        server_1 = Mock()
        server_1.server_name = "SAN-01"

        server_2 = Mock()
        server_2.server_name = "SAN-02"

        mock_monitoring_scheduler.run.return_value = {
            "successful": [server_1],
            "failed": [
                {
                    "server": server_2,
                    "error": "Authentication failed.",
                }
            ],
        }

        output = StringIO()

        call_command(
            "monitor_servers",
            stdout=output,
        )

        result = output.getvalue()

        self.assertIn("Successful servers: 1", result)
        self.assertIn("Failed servers: 1", result)
        self.assertIn("SAN-02", result)
        self.assertIn("Authentication failed.", result)