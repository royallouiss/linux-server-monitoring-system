import time


class CPUCollector:
    CPU_FIELDS = [
        "user",
        "nice",
        "system",
        "idle",
        "iowait",
        "irq",
        "softirq",
        "steal",
    ]

    def __init__(self, ssh, interval=1):
        self.ssh = ssh
        self.interval = interval

    def collect(self):
        success, output = self.ssh.execute_command(
            "cat /proc/stat | head -n 1"
        )

        if not success:
            raise RuntimeError(output)

        sample_1 = self.parse_cpu_stats(output)

        success, output = self.ssh.execute_command("nproc")

        if not success:
            raise RuntimeError(output)

        logical_cpus = self.parse_logical_cpus(output)

        success, output = self.ssh.execute_command("cat /proc/loadavg")

        if not success:
            raise RuntimeError(output)

        load_average = self.parse_load_average(output)

        time.sleep(self.interval)

        success, output = self.ssh.execute_command(
            "cat /proc/stat | head -n 1"
        )

        if not success:
            raise RuntimeError(output)

        sample_2 = self.parse_cpu_stats(output)

        usage_percent = self.calculate_usage(sample_1, sample_2)

        return {
            "logical_cpus": logical_cpus,
            "usage_percent": usage_percent,
            "load_average": load_average,
        }

    @staticmethod
    def calculate_usage(sample_1, sample_2):
        total_1 = sum(sample_1.values())
        total_2 = sum(sample_2.values())

        total_delta = total_2 - total_1

        if total_delta <= 0:
            return 0.0

        idle_delta = sample_2["idle"] - sample_1["idle"]
        iowait_delta = sample_2["iowait"] - sample_1["iowait"]

        if idle_delta < 0 or iowait_delta < 0:
            raise ValueError("CPU counters moved backwards.")

        busy_delta = total_delta - idle_delta - iowait_delta

        if busy_delta < 0:
            raise ValueError("Invalid CPU counter values.")

        return (busy_delta / total_delta) * 100

    @staticmethod
    def parse_cpu_stats(output):
        lines = output.strip().splitlines()

        if not lines:
            raise ValueError("CPU statistics are empty.")

        parts = lines[0].split()

        if parts[0] != "cpu":
            raise ValueError("Invalid CPU statistics.")

        values = parts[1:]

        if len(values) < len(CPUCollector.CPU_FIELDS):
            raise ValueError("Incomplete CPU statistics.")

        try:
            values = [int(value) for value in values]
        except ValueError as error:
            raise ValueError("CPU statistics contain invalid values.") from error

        return dict(
            zip(
                CPUCollector.CPU_FIELDS,
                values,
            )
        )

    @staticmethod
    def parse_load_average(output):
        parts = output.split()

        if len(parts) < 3:
            raise ValueError("Invalid load average.")

        try:
            return {
                "1m": float(parts[0]),
                "5m": float(parts[1]),
                "15m": float(parts[2]),
            }
        except ValueError as error:
            raise ValueError("Load average contains invalid values.") from error

    @staticmethod
    def parse_logical_cpus(output):
        try:
            logical_cpus = int(output.strip())
        except ValueError as error:
            raise ValueError("Invalid logical CPU count.") from error

        if logical_cpus <= 0:
            raise ValueError("Logical CPU count must be greater than zero.")

        return logical_cpus