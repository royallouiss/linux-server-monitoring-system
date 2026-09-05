from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class MonitoringCommandTests(SimpleTestCase):
    @patch(
        "linux_server_monitoring_system.monitoring.management.commands.monitor_servers.MonitoringScheduler"
    )
    def test_runs_monitoring_scheduler(self, mock_monitoring_scheduler):
        output = StringIO()

        call_command(
            "monitor_servers",
            stdout=output,
        )

        mock_monitoring_scheduler.run.assert_called_once_with()

        self.assertIn(
            "Monitoring completed successfully.",
            output.getvalue(),
        )