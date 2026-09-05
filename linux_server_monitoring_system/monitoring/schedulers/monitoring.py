from linux_server_monitoring_system.monitoring.runners.monitoring import (
    MonitoringRunner,
)
from linux_server_monitoring_system.servers.models import Server


class MonitoringScheduler:
    @staticmethod
    def run():
        servers = Server.objects.filter(is_active=True)

        return MonitoringRunner.run(servers)