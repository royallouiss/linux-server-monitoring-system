class MemoryCollector:
    def __init__(self, ssh):
        self.ssh = ssh

    def collect(self):
        success, output = self.ssh.execute_command("free -b")

        if not success:
            raise RuntimeError(output)

        return self._parse(output)

    def _parse(self, output):
        memory = None
        swap = None

        for line in output.splitlines():
            parts = line.split()

            if not parts:
                continue

            if parts[0] == "Mem:":
                memory = {
                    "total_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]),
                    "available_bytes": int(parts[6]),
                }

            elif parts[0] == "Swap:":
                swap = {
                    "total_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]),
                }

        if memory is None:
            raise ValueError("Memory information not found.")

        if swap is None:
            raise ValueError("Swap information not found.")

        memory["usage_percent"] = (
            memory["used_bytes"] / memory["total_bytes"]
        ) * 100

        swap["usage_percent"] = (
            swap["used_bytes"] / swap["total_bytes"] * 100
            if swap["total_bytes"]
            else 0.0
        )

        return {
            "memory": memory,
            "swap": swap,
        }