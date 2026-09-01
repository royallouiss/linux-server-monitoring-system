from linux_server_monitoring_system.monitoring.services.monitoring import (
    MonitoringService,
)


class MonitoringJob:
    @staticmethod
    def run(server):
        service = MonitoringService.for_server(server)
        service.collect()