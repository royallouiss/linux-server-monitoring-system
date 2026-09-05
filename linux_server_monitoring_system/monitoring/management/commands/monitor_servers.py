from django.core.management.base import BaseCommand

from linux_server_monitoring_system.monitoring.schedulers.monitoring import (
    MonitoringScheduler,
)


class Command(BaseCommand):
    help = "Run monitoring for all active servers."

    def handle(self, *args, **options):
        MonitoringScheduler.run()

        self.stdout.write(
            self.style.SUCCESS(
                "Monitoring completed successfully."
            )
        )