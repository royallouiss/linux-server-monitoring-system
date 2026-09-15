from linux_server_monitoring_system.monitoring.jobs.monitoring import (
    MonitoringJob,
)


class MonitoringRunner:
    @staticmethod
    def run(servers):
        successful = []
        failed = []

        for server in servers:
            try:
                MonitoringJob.run(server)
                successful.append(server)
            except Exception as error:
                failed.append(
                    {
                        "server": server,
                        "error": str(error),
                    }
                )

        return {
            "successful": successful,
            "failed": failed,
        }