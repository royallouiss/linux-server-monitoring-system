from django.utils import timezone

from linux_server_monitoring_system.monitoring.services.monitoring import (
    MonitoringService,
)


class MonitoringJob:
    @staticmethod
    def run(server):
        check_time = timezone.now()

        try:
            service = MonitoringService.for_server(server)
            service.collect()
        except Exception as error:
            server.status = "DOWN"
            server.last_check_at = check_time
            server.last_error = str(error)

            server.save(
                update_fields=[
                    "status",
                    "last_check_at",
                    "last_error",
                ]
            )

            raise

        server.status = "UP"
        server.last_check_at = check_time
        server.last_success_at = check_time
        server.last_error = ""

        server.save(
            update_fields=[
                "status",
                "last_check_at",
                "last_success_at",
                "last_error",
            ]
        )