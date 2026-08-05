from django.core.management.base import BaseCommand

from linux_server_monitoring_system.core.ssh import SSHService
from linux_server_monitoring_system.servers.models import Server


class Command(BaseCommand):
    help = "Test SSH connection to a registered server."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Testing SSH connection..."))

        # Get the first registered server
        server = Server.objects.first()

        if not server:
            self.stdout.write(
                self.style.ERROR("No server found in the database.")
            )
            return

        # Display server information
        self.stdout.write(f"Server : {server.server_name}")
        self.stdout.write(f"Host   : {server.hostname}")
        self.stdout.write(f"User   : {server.username}")
        self.stdout.write(f"Port   : {server.ssh_port}")

        # Create SSH service
        ssh = SSHService()

        # Connect to the server
        success, message = ssh.connect(
            hostname=server.hostname,
            port=server.ssh_port,
            username=server.username,
            password=server.password,
        )

        if not success:
            self.stdout.write(self.style.ERROR(message))
            return

        self.stdout.write(self.style.SUCCESS(message))

        # Execute hostname command
        success, output = ssh.execute_command("hostname")

        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Hostname : {output}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(output)
            )

        # Disconnect
        ssh.disconnect()

        self.stdout.write(
            self.style.SUCCESS("SSH connection closed.")
        )