import time


class NetworkCollector:
    EXCLUDED_INTERFACES = {
        "lo",
    }

    def __init__(self, ssh, interval=1):
        self.ssh = ssh
        self.interval = interval

    def collect(self):
        success, output = self.ssh.execute_command(
            "cat /proc/net/dev"
        )

        if not success:
            raise RuntimeError(output)

        previous = self.parse_network_stats(output)

        time.sleep(self.interval)

        success, output = self.ssh.execute_command(
            "cat /proc/net/dev"
        )

        if not success:
            raise RuntimeError(output)

        current = self.parse_network_stats(output)

        rates = self.calculate_rates(
            previous,
            current,
            self.interval,
        )

        result = {}

        for interface, stats in current.items():
            result[interface] = {
                "received_bytes": stats["received_bytes"],
                "transmitted_bytes": stats["transmitted_bytes"],
                "receive_rate": rates.get(
                    interface,
                    {},
                ).get("receive_rate", 0.0),
                "transmit_rate": rates.get(
                    interface,
                    {},
                ).get("transmit_rate", 0.0),
            }

        return result

    @staticmethod
    def parse_network_stats(output):
        lines = output.strip().splitlines()

        result = {}

        for line in lines[2:]:
            if ":" not in line:
                continue

            interface, data = line.split(":", 1)
            interface = interface.strip()

            if interface in NetworkCollector.EXCLUDED_INTERFACES:
                continue

            parts = data.split()

            received_bytes = int(parts[0])
            transmitted_bytes = int(parts[8])

            result[interface] = {
                "received_bytes": received_bytes,
                "transmitted_bytes": transmitted_bytes,
            }

        return result

    @staticmethod
    def calculate_rates(previous, current, interval):
        if interval <= 0:
            interval = 1

        result = {}

        for interface, current_stats in current.items():
            if interface not in previous:
                continue

            previous_stats = previous[interface]

            received_delta = (
                current_stats["received_bytes"]
                - previous_stats["received_bytes"]
            )

            transmitted_delta = (
                current_stats["transmitted_bytes"]
                - previous_stats["transmitted_bytes"]
            )

            if received_delta < 0:
                received_delta = 0

            if transmitted_delta < 0:
                transmitted_delta = 0

            result[interface] = {
                "receive_rate": received_delta / interval,
                "transmit_rate": transmitted_delta / interval,
            }

        return result