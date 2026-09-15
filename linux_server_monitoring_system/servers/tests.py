from unittest.mock import patch

from django.test import TestCase

from linux_server_monitoring_system.monitoring.jobs.monitoring import (
    MonitoringJob,
)
from linux_server_monitoring_system.servers.models import Server


class ServerHealthTests(TestCase):
    def create_server(self):
        return Server.objects.create(
            server_name="Test Server",
            hostname="192.168.1.100",
            username="testuser",
            password="testpassword",
        )

    def test_new_server_has_unknown_status(self):
        server = self.create_server()

        self.assertEqual(server.status, "UNKNOWN")
        self.assertIsNone(server.last_check_at)
        self.assertIsNone(server.last_success_at)
        self.assertEqual(server.last_error, "")

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_successful_monitoring_persists_server_health(
        self,
        mock_monitoring_service,
    ):
        server = self.create_server()

        service = mock_monitoring_service.for_server.return_value

        MonitoringJob.run(server)

        service.collect.assert_called_once_with()

        server.refresh_from_db()

        self.assertEqual(server.status, "UP")
        self.assertIsNotNone(server.last_check_at)
        self.assertIsNotNone(server.last_success_at)
        self.assertEqual(server.last_error, "")

    @patch(
        "linux_server_monitoring_system.monitoring.jobs.monitoring.MonitoringService"
    )
    def test_failed_monitoring_persists_server_health(
        self,
        mock_monitoring_service,
    ):
        server = self.create_server()

        mock_monitoring_service.for_server.side_effect = RuntimeError(
            "SSH connection failed."
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "SSH connection failed.",
        ):
            MonitoringJob.run(server)

        server.refresh_from_db()

        self.assertEqual(server.status, "DOWN")
        self.assertIsNotNone(server.last_check_at)
        self.assertIsNone(server.last_success_at)
        self.assertEqual(
            server.last_error,
            "SSH connection failed.",
        )


class DashboardApiTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.server = Server.objects.create(
            server_name="Prod Web 01",
            hostname="192.168.1.50",
            ssh_port=22,
            username="adminuser",
            password="secretpassword",
            status="UP",
        )

    def test_dashboard_stats_endpoint(self):
        response = self.client.get("/api/dashboard/stats/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_servers", data)
        self.assertIn("online_servers", data)
        self.assertIn("warning_servers", data)
        self.assertIn("offline_servers", data)
        self.assertIn("active_alerts", data)
        self.assertIn("monitoring_success_rate", data)
        self.assertIn("system_status", data)
        self.assertIn("monitoring_engine", data)
        self.assertIn("tasks", data)
        self.assertIn("resource_sparklines", data)
        self.assertEqual(data["total_servers"], 1)
        self.assertEqual(data["online_servers"], 1)
        self.assertEqual(data["system_status"], "HEALTHY")
        self.assertIn("service_status", data["monitoring_engine"])
        self.assertIn("scheduler_status", data["monitoring_engine"])
        self.assertIn("runner_status", data["monitoring_engine"])

    def test_system_status_transitions(self):
        from linux_server_monitoring_system.servers.models import Alert

        # Initially 1 server UP -> HEALTHY
        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.json()["system_status"], "HEALTHY")

        # Add WARNING alert -> WARNING
        warn_alert = Alert.objects.create(
            server=self.server,
            title="High Disk Usage",
            severity=Alert.Severity.WARNING,
            status=Alert.Status.ACTIVE,
        )
        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.json()["system_status"], "WARNING")
        self.assertEqual(resp.json()["warning_servers"], 1)

        # Make server DOWN -> CRITICAL
        self.server.status = "DOWN"
        self.server.save()
        resp = self.client.get("/api/dashboard/stats/")
        self.assertEqual(resp.json()["system_status"], "CRITICAL")
        self.assertEqual(resp.json()["offline_servers"], 1)

    def test_server_serializer_health_status(self):
        from linux_server_monitoring_system.servers.api.serializers import ServerSerializer

        # UP -> HEALTHY
        self.assertEqual(ServerSerializer(self.server).data["health_status"], "HEALTHY")

        # DOWN -> OFFLINE
        self.server.status = "DOWN"
        self.server.save()
        self.assertEqual(ServerSerializer(self.server).data["health_status"], "OFFLINE")

        # UNKNOWN -> UNKNOWN
        self.server.status = "UNKNOWN"
        self.server.save()
        self.assertEqual(ServerSerializer(self.server).data["health_status"], "UNKNOWN")

    def test_server_list_security_no_password_exposed(self):
        response = self.client.get("/api/servers/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["server_name"], "Prod Web 01")
        self.assertNotIn("password", data[0])
        self.assertIn("health_status", data[0])

    def test_server_metrics_endpoint(self):
        from django.utils import timezone
        from linux_server_monitoring_system.monitoring.models import MetricSample

        MetricSample.objects.create(
            server=self.server,
            metric_name="cpu_usage",
            value=45.5,
            unit="percent",
            timestamp=timezone.now(),
        )

        response = self.client.get(f"/api/servers/{self.server.id}/metrics/?range=1h")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["server_id"], self.server.id)
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("disk", data)
        self.assertIn("network_rx", data)
        self.assertEqual(len(data["cpu"]), 1)
        self.assertEqual(data["cpu"][0], 45.5)
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["cpu"]["current"], 45.5)
        self.assertEqual(data["summary"]["cpu"]["peak"], 45.5)
        self.assertEqual(data["interval_seconds"], 10)

    @patch("linux_server_monitoring_system.servers.api.views.SSHService")
    def test_server_test_connection_action(self, mock_ssh_cls):
        mock_ssh = mock_ssh_cls.return_value
        mock_ssh.connect.return_value = (True, "Connection successful.")
        mock_ssh.execute_command.return_value = (True, "ubuntu-host")

        response = self.client.post(
            f"/api/servers/{self.server.id}/test_connection/"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "UP")
        self.assertEqual(data["hostname"], "ubuntu-host")

    def test_alert_list_and_resolve(self):
        from linux_server_monitoring_system.servers.models import Alert

        alert = Alert.objects.create(
            server=self.server,
            title="High Memory Usage",
            message="Memory utilization reached 92%",
            severity=Alert.Severity.WARNING,
            status=Alert.Status.ACTIVE,
        )

        # Test list
        response = self.client.get("/api/alerts/?status=ACTIVE")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "High Memory Usage")

        # Test resolve action
        resolve_resp = self.client.post(f"/api/alerts/{alert.id}/resolve/")
        self.assertEqual(resolve_resp.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.RESOLVED)
        self.assertIsNotNone(alert.resolved_at)

    def test_unauthenticated_api_rejected(self):
        from rest_framework.test import APIClient

        unauth_client = APIClient()
        response = unauth_client.get("/api/dashboard/stats/")
        self.assertIn(response.status_code, [401, 403])

    def test_dashboard_requires_authentication(self):
        from django.test import Client

        anon_client = Client()
        response = anon_client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_authenticated_access(self):
        from django.test import Client

        auth_client = Client()
        auth_client.force_login(self.admin_user)
        response = auth_client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("dashboard-app", content)
        self.assertIn("system-command-bar", content)
        self.assertIn("servers-table-body", content)
        self.assertIn("section-heatmap", content)
        self.assertIn("section-alerts-tasks", content)
        self.assertIn("section-engine", content)
        self.assertIn("refresh-countdown-badge", content)
        self.assertIn("dashboard.js", content)
        self.assertIn("dashboard.css", content)


class AdminUiUxTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import Client
        from linux_server_monitoring_system.servers.models import Alert

        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            email="admin_ui@example.com",
            password="adminpassword",
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.server = Server.objects.create(
            server_name="Admin Test Server",
            hostname="10.0.0.1",
            username="admin",
            password="pwd",
        )
        self.alert = Alert.objects.create(
            server=self.server,
            title="High CPU Alert",
            severity=Alert.Severity.WARNING,
            status=Alert.Status.ACTIVE,
        )

    def test_admin_index_branding_and_hero_kpis(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Linux Server Monitoring System", content)
        self.assertIn("Live Dashboard", content)
        self.assertIn("admin-hero-grid", content)
        self.assertIn("Monitored Fleet", content)
        self.assertIn("Fleet Availability", content)
        self.assertIn("admin_theme.css", content)

    def test_server_admin_changelist(self):
        response = self.client.get("/admin/servers/server/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("test_ssh_connectivity", content)

    def test_alert_admin_changelist_actions(self):
        response = self.client.get("/admin/servers/alert/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("mark_resolved", content)
        self.assertIn("mark_active", content)

    def test_metric_sample_admin_registered(self):
        response = self.client.get("/admin/monitoring/metricsample/")
        self.assertEqual(response.status_code, 200)

