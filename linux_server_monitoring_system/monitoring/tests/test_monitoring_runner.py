from unittest.mock import Mock, patch

from django.test import SimpleTestCase


class MonitoringRunnerTests(SimpleTestCase):
    @patch(
        "linux_server_monitoring_system.monitoring.runners.monitoring.MonitoringJob"
    )
    def test_runs_monitoring_for_each_active_server(
        self,
        mock_monitoring_job,
    ):
        from linux_server_monitoring_system.monitoring.runners.monitoring import (
            MonitoringRunner,
        )

        server_1 = object()
        server_2 = object()
        server_3 = object()

        servers = [
            server_1,
            server_2,
            server_3,
        ]

        result = MonitoringRunner.run(servers)

        self.assertEqual(
            result,
            {
                "successful": [
                    server_1,
                    server_2,
                    server_3,
                ],
                "failed": [],
            },
        )

        self.assertEqual(
            mock_monitoring_job.run.call_count,
            3,
        )

        mock_monitoring_job.run.assert_any_call(server_1)
        mock_monitoring_job.run.assert_any_call(server_2)
        mock_monitoring_job.run.assert_any_call(server_3)

    @patch(
        "linux_server_monitoring_system.monitoring.runners.monitoring.MonitoringJob"
    )
    def test_continues_when_one_server_fails(
        self,
        mock_monitoring_job,
    ):
        from linux_server_monitoring_system.monitoring.runners.monitoring import (
            MonitoringRunner,
        )

        server_1 = object()
        server_2 = Mock()
        server_2.server_name = "Server 2"
        server_3 = object()

        mock_monitoring_job.run.side_effect = [
            None,
            RuntimeError("SSH connection failed."),
            None,
        ]

        result = MonitoringRunner.run(
            [
                server_1,
                server_2,
                server_3,
            ]
        )

        self.assertEqual(
            result["successful"],
            [
                server_1,
                server_3,
            ],
        )

        self.assertEqual(
            len(result["failed"]),
            1,
        )

        self.assertIs(
            result["failed"][0]["server"],
            server_2,
        )

        self.assertEqual(
            result["failed"][0]["error"],
            "SSH connection failed.",
        )

        self.assertEqual(
            mock_monitoring_job.run.call_count,
            3,
        )

    @patch(
        "linux_server_monitoring_system.monitoring.runners.monitoring.MonitoringJob"
    )
    def test_returns_empty_result_when_no_servers(
        self,
        mock_monitoring_job,
    ):
        from linux_server_monitoring_system.monitoring.runners.monitoring import (
            MonitoringRunner,
        )

        result = MonitoringRunner.run([])

        self.assertEqual(
            result,
            {
                "successful": [],
                "failed": [],
            },
        )

        mock_monitoring_job.run.assert_not_called()