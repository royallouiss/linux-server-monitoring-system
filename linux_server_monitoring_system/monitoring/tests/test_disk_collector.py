from django.test import SimpleTestCase

from linux_server_monitoring_system.monitoring.collectors.disk import (
    DiskCollector,
)


class TestDiskCollector(SimpleTestCase):

    def test_parse_disk_usage(self):
        output = """\
Filesystem  1B-blocks        Used     Available  Use%  Mounted on
/dev/sda1   107374182400    66571993088  40801996800  62%   /
/dev/sda2   214748364800    107374182400 107374182400 50%   /home
"""

        result = DiskCollector.parse_disk_usage(output)

        self.assertEqual(
            result,
            {
                "/": {
                    "total_bytes": 107374182400,
                    "used_bytes": 66571993088,
                    "available_bytes": 40801996800,
                    "usage_percent": 62.0,
                },
            },
        )

    def test_parse_disk_usage_rejects_invalid_output(self):
        output = """\
Filesystem  1B-blocks  Used  Available  Use%  Mounted on
/dev/sda1   invalid    100   200         50%   /
"""

        with self.assertRaises(ValueError):
            DiskCollector.parse_disk_usage(output)

    def test_collect(self):
        class FakeSSHService:
            def execute_command(self, command):
                self.command = command

                output = """\
Filesystem  1B-blocks        Used     Available  Use%  Mounted on
/dev/sda1   107374182400    66571993088  40801996800  62%   /
/dev/sda2   214748364800    107374182400 107374182400 50%   /home
"""

                return True, output

        ssh = FakeSSHService()
        collector = DiskCollector(ssh)

        result = collector.collect()

        self.assertEqual(ssh.command, "df -B1")
        self.assertEqual(
            result["/"]["usage_percent"],
            62.0,
        )
        self.assertNotIn("/home", result)

    def test_collect_raises_error_when_ssh_command_fails(self):
        class FakeSSHService:
            def execute_command(self, command):
                return False, "SSH command failed."

        collector = DiskCollector(FakeSSHService())

        with self.assertRaisesRegex(
            RuntimeError,
            "SSH command failed.",
        ):
            collector.collect()

    def test_parse_disk_usage_handles_wsl_filesystem_names(self):
        output = """\
Filesystem         1B-blocks         Used     Available Use% Mounted on
C:\\             510403088384 421909516288   88493572096  83% /mnt/c
/dev/sdd       1081101176832   1768165376 1024340656128   1% /
"""

        result = DiskCollector.parse_disk_usage(output)

        self.assertEqual(
            list(result.keys()),
            ["/"],
        )

        self.assertEqual(
            result["/"]["usage_percent"],
            1.0,
        )

    def test_parse_disk_usage_ignores_virtual_filesystems(self):
        output = """\
Filesystem         1B-blocks         Used     Available Use% Mounted on
/dev/sdd       1081101176832   1768165376 1024340656128   1% /
/dev/sda2        214748364800 107374182400 107374182400 50% /home
tmpfs              4000000000            0    4000000000   0% /tmp
none               4000000000            0    4000000000   0% /mnt/wsl
none               4000000000            0    4000000000   0% /run
"""

        result = DiskCollector.parse_disk_usage(output)

        self.assertEqual(
            list(result.keys()),
            ["/"],
        )

        self.assertNotIn("/home", result)
        self.assertNotIn("/tmp", result)
        self.assertNotIn("/mnt/wsl", result)
        self.assertNotIn("/run", result)