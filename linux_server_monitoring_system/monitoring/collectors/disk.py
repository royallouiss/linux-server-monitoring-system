class DiskCollector:
    MONITORED_MOUNT_POINTS = {
        "/",
    }

    EXCLUDED_FILESYSTEMS = {
        "tmpfs",
        "devtmpfs",
        "none",
        "overlay",
    }

    EXCLUDED_MOUNT_PREFIXES = (
        "/proc",
        "/sys",
        "/dev",
        "/run",
    )

    def __init__(self, ssh):
        self.ssh = ssh

    def collect(self):
        success, output = self.ssh.execute_command("df -B1")

        if not success:
            raise RuntimeError(output)

        return self.parse_disk_usage(output)

    @staticmethod
    def parse_disk_usage(output):
        lines = output.strip().splitlines()

        result = {}

        for line in lines[1:]:
            parts = line.split()

            filesystem = parts[0]
            mount_point = parts[5]

            if filesystem in DiskCollector.EXCLUDED_FILESYSTEMS:
                continue

            if mount_point.startswith(
                DiskCollector.EXCLUDED_MOUNT_PREFIXES
            ):
                continue

            if mount_point not in DiskCollector.MONITORED_MOUNT_POINTS:
                continue

            total_bytes = int(parts[1])
            used_bytes = int(parts[2])
            available_bytes = int(parts[3])
            usage_percent = float(parts[4].rstrip("%"))

            result[mount_point] = {
                "total_bytes": total_bytes,
                "used_bytes": used_bytes,
                "available_bytes": available_bytes,
                "usage_percent": usage_percent,
            }

        return result