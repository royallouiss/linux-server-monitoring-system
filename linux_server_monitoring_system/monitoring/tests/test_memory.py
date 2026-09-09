from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.collectors.memory import (
    MemoryCollector,
)


class FakeSSHService:
    def __init__(self, output):
        self.output = output

    def execute_command(self, command):
        return True, self.output


class MemoryCollectorTests(SimpleTestCase):
    def test_collects_memory_and_swap_metrics(self):
        output = """\
               total        used        free      shared  buff/cache   available
Mem:      8017051648   620027904  6871568384     3690496   684113920  7397023744
Swap:     2147483648           0  2147483648
"""

        ssh = FakeSSHService(output)
        collector = MemoryCollector(ssh)

        result = collector.collect()

        self.assertEqual(result["memory"]["total_bytes"], 8017051648)
        self.assertEqual(result["memory"]["used_bytes"], 620027904)
        self.assertEqual(result["memory"]["available_bytes"], 7397023744)

        self.assertEqual(result["swap"]["total_bytes"], 2147483648)
        self.assertEqual(result["swap"]["used_bytes"], 0)
        self.assertAlmostEqual(
            result["memory"]["usage_percent"],
            (620027904 / 8017051648) * 100,
        )

        self.assertEqual(
            result["swap"]["usage_percent"],
            0.0,)
