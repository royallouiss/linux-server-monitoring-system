from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.collectors.cpu import CPUCollector


class CPUCollectorTests(SimpleTestCase):
    def test_calculates_cpu_usage(self):
        sample_1 = {
            "user": 100,
            "nice": 0,
            "system": 50,
            "idle": 800,
            "iowait": 20,
            "irq": 0,
            "softirq": 0,
            "steal": 0,
        }

        sample_2 = {
            "user": 120,
            "nice": 0,
            "system": 55,
            "idle": 820,
            "iowait": 20,
            "irq": 0,
            "softirq": 0,
            "steal": 0,
        }

        usage = CPUCollector.calculate_usage(sample_1, sample_2)

        self.assertAlmostEqual(usage, 55.56, places=2)

    def test_parses_cpu_stats(self):
        output = "cpu  426 0 505 68186 147 0 106 0 0 0"

        result = CPUCollector.parse_cpu_stats(output)

        self.assertEqual(
            result,
            {
                "user": 426,
                "nice": 0,
                "system": 505,
                "idle": 68186,
                "iowait": 147,
                "irq": 0,
                "softirq": 106,
                "steal": 0,
            },
        )

    def test_parses_load_average(self):
        output = "0.15 0.05 0.01 1/223 614"

        result = CPUCollector.parse_load_average(output)

        self.assertEqual(
            result,
            {
                "1m": 0.15,
                "5m": 0.05,
                "15m": 0.01,
            },
        )

    def test_parses_logical_cpu_count(self):
        output = "8\n"

        result = CPUCollector.parse_logical_cpus(output)

        self.assertEqual(result, 8)

    def test_collects_cpu_metrics(self):
        class FakeSSHService:
            def __init__(self):
                self.stat_calls = 0

            def execute_command(self, command):
                if command == "cat /proc/stat | head -n 1":
                    self.stat_calls += 1

                    if self.stat_calls == 1:
                        return True, "cpu 100 0 50 800 20 0 0 0 0 0"

                    return True, "cpu 120 0 55 820 20 0 0 0 0 0"

                if command == "nproc":
                    return True, "8\n"

                if command == "cat /proc/loadavg":
                    return True, "0.15 0.05 0.01 1/223 614"

                return False, "Unknown command"

        ssh = FakeSSHService()

        collector = CPUCollector(ssh, interval=0)

        result = collector.collect()

        self.assertEqual(result["logical_cpus"], 8)

        self.assertEqual(
            result["load_average"],
            {
                "1m": 0.15,
                "5m": 0.05,
                "15m": 0.01,
            },
        )

        self.assertAlmostEqual(
            result["usage_percent"],
            55.56,
            places=2,
        )

    def test_rejects_invalid_cpu_stats(self):
        output = "invalid cpu data"

        with self.assertRaises(ValueError):
            CPUCollector.parse_cpu_stats(output)