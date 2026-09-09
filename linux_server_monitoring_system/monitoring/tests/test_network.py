from unittest.mock import patch

from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.collectors.network import (
    NetworkCollector,
)


class TestNetworkCollector(SimpleTestCase):

    def test_parse_network_stats(self):
        output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    eth0: 1000000  1000    0    0    0     0          0         0  2000000  2000    0    0    0     0       0          0
"""

        result = NetworkCollector.parse_network_stats(output)

        self.assertEqual(
            result,
            {
                "eth0": {
                    "received_bytes": 1000000,
                    "transmitted_bytes": 2000000,
                },
            },
        )

    def test_parse_network_stats_ignores_loopback(self):
        output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
      lo: 500000  500    0    0    0     0          0         0  500000  500    0    0    0     0       0          0
    eth0: 1000000 1000    0    0    0     0          0         0  2000000 2000    0    0    0     0       0          0
"""

        result = NetworkCollector.parse_network_stats(output)

        self.assertNotIn("lo", result)
        self.assertIn("eth0", result)

    def test_parse_network_stats_rejects_invalid_output(self):
        output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    eth0: invalid 1000 0 0 0 0 0 0 2000000 2000 0 0 0 0 0 0
"""

        with self.assertRaises(ValueError):
            NetworkCollector.parse_network_stats(output)

    @patch(
        "linux_server_monitoring_system.monitoring.collectors.network.time.sleep"
    )
    def test_collect(self, mock_sleep):
        class FakeSSHService:
            def execute_command(self, command):
                self.command = command

                output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    eth0: 1000000 1000    0    0    0     0          0         0  2000000 2000    0    0    0     0       0          0
"""

                return True, output

        ssh = FakeSSHService()
        collector = NetworkCollector(ssh)

        result = collector.collect()

        mock_sleep.assert_called_once_with(1)

        self.assertEqual(
            ssh.command,
            "cat /proc/net/dev",
        )

        self.assertEqual(
            result["eth0"]["received_bytes"],
            1000000,
        )

        self.assertEqual(
            result["eth0"]["transmitted_bytes"],
            2000000,
        )

    def test_collect_raises_error_when_ssh_command_fails(self):
        class FakeSSHService:
            def execute_command(self, command):
                return False, "SSH command failed."

        collector = NetworkCollector(FakeSSHService())

        with self.assertRaisesRegex(
            RuntimeError,
            "SSH command failed.",
        ):
            collector.collect()

    def test_calculate_rates(self):
        previous = {
            "eth0": {
                "received_bytes": 1000000,
                "transmitted_bytes": 2000000,
            },
        }

        current = {
            "eth0": {
                "received_bytes": 1500000,
                "transmitted_bytes": 2200000,
            },
        }

        result = NetworkCollector.calculate_rates(
            previous,
            current,
            interval=1,
        )

        self.assertEqual(
            result,
            {
                "eth0": {
                    "receive_rate": 500000.0,
                    "transmit_rate": 200000.0,
                },
            },
        )

    @patch(
        "linux_server_monitoring_system.monitoring.collectors.network.time.sleep"
    )
    def test_collect_calculates_network_rates(self, mock_sleep):
        class FakeSSHService:
            def __init__(self):
                self.call_count = 0

            def execute_command(self, command):
                self.call_count += 1

                if self.call_count == 1:
                    output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    eth0: 1000000 1000    0    0    0     0          0         0  2000000 2000    0    0    0     0       0          0
"""
                else:
                    output = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    eth0: 1500000 1500    0    0    0     0          0         0  2200000 2200    0    0    0     0       0          0
"""

                return True, output

        ssh = FakeSSHService()
        collector = NetworkCollector(ssh)

        result = collector.collect()

        mock_sleep.assert_called_once_with(1)

        self.assertEqual(
            result["eth0"]["received_bytes"],
            1500000,
        )

        self.assertEqual(
            result["eth0"]["transmitted_bytes"],
            2200000,
        )

        self.assertEqual(
            result["eth0"]["receive_rate"],
            500000.0,
        )

        self.assertEqual(
            result["eth0"]["transmit_rate"],
            200000.0,
        )

    def test_calculate_rates_handles_counter_reset(self):
        previous = {
            "eth0": {
                "received_bytes": 5000000,
                "transmitted_bytes": 8000000,
            },
        }

        current = {
            "eth0": {
                "received_bytes": 100000,
                "transmitted_bytes": 200000,
            },
        }

        result = NetworkCollector.calculate_rates(
            previous,
            current,
            interval=1,
        )

        self.assertEqual(
            result,
            {
                "eth0": {
                    "receive_rate": 0.0,
                    "transmit_rate": 0.0,
                },
            },
        )

    def test_calculate_rates_ignores_new_interfaces(self):
        previous = {
            "eth0": {
                "received_bytes": 1000000,
                "transmitted_bytes": 2000000,
            },
        }

        current = {
            "eth0": {
                "received_bytes": 1500000,
                "transmitted_bytes": 2200000,
            },
            "eth1": {
                "received_bytes": 500000,
                "transmitted_bytes": 700000,
            },
        }

        result = NetworkCollector.calculate_rates(
            previous,
            current,
            interval=1,
        )

        self.assertIn("eth0", result)
        self.assertNotIn("eth1", result)

        self.assertEqual(
            result["eth0"]["receive_rate"],
            500000.0,
        )

        self.assertEqual(
            result["eth0"]["transmit_rate"],
            200000.0,
        )