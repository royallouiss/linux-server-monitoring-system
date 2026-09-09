from django.core.management.base import BaseCommand

from linux_server_monitoring_system.monitoring.schedulers.monitoring import (
    MonitoringScheduler,
)


class Command(BaseCommand):
    help = "Run monitoring for all active servers."

    def handle(self, *args, **options):
        result = MonitoringScheduler.run()

        successful = result["successful"]
        failed = result["failed"]

        self.stdout.write("Monitoring completed.")
        self.stdout.write(f"Successful servers: {len(successful)}")
        self.stdout.write(f"Failed servers: {len(failed)}")

        if failed:
            self.stdout.write("")
            self.stdout.write("Failed servers:")

            for failure in failed:
                server = failure["server"]
                error = failure["error"]

                self.stdout.write(
                f"- {server.server_name}: {error}"
            )