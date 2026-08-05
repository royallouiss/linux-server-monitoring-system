import paramiko


class SSHService:
    # """
    # Service responsible for SSH communication with remote Linux servers.
    # """

    def __init__(self):
        self.client = None

    def connect(self, hostname, port, username, password):
    # """
    # Establish an SSH connection to a remote server.
    # """

        try:
            self.client = paramiko.SSHClient()

            self.client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )

            self.client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                timeout=10,
            )

            return True, "Connection successful."

        except paramiko.AuthenticationException:
            return False, "Authentication failed."

        except paramiko.SSHException as error:
            return False, f"SSH error: {error}"

        except Exception as error:
            return False, f"Unexpected error: {error}"

    def disconnect(self):
    # """
    # Close the SSH connection if it exists.
    # """

        if self.client:
            self.client.close()
            self.client = None    

    def execute_command(self, command):
    # """
    # Execute a command on the connected server.
    # """

        if not self.client:
            return False, "No active SSH connection."

        try:
            stdin, stdout, stderr = self.client.exec_command(command)

            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                return False, error

            return True, output

        except Exception as error:
            return False, str(error)