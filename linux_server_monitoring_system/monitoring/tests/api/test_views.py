import pytest
from rest_framework.test import APIClient

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Server
from linux_server_monitoring_system.users.models import User


pytestmark = pytest.mark.django_db


class TestServerAPI:
    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="api_test@example.com",
            password="testpassword123",
        )

        self.client.force_authenticate(user=self.user)

        self.server = Server.objects.create(
            server_name="Test Server",
            hostname="192.168.1.100",
            ssh_port=22,
            username="testuser",
            password="testpassword",
            operating_system="UBUNTU",
            description="Test server",
            is_active=True,
        )

    def test_server_list(self):
        response = self.client.get("/api/servers/")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["server_name"] == "Test Server"

    def test_server_detail(self):
        response = self.client.get(
            f"/api/servers/{self.server.id}/",
        )

        assert response.status_code == 200
        assert response.data["id"] == self.server.id
        assert response.data["server_name"] == "Test Server"

    def test_server_metrics(self):
        MetricSample.objects.create(
            server=self.server,
            metric_name="cpu",
            value=45.5,
            unit="%",
            timestamp="2026-09-13T10:00:00Z",
        )

        response = self.client.get(
            f"/api/servers/{self.server.id}/metrics/",
        )

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["metric_name"] == "cpu"

    def test_specific_metric(self):
        MetricSample.objects.create(
            server=self.server,
            metric_name="cpu",
            value=45.5,
            unit="%",
            timestamp="2026-09-13T10:00:00Z",
        )

        MetricSample.objects.create(
            server=self.server,
            metric_name="memory",
            value=70.0,
            unit="%",
            timestamp="2026-09-13T10:01:00Z",
        )

        response = self.client.get(
            f"/api/servers/{self.server.id}/metrics/cpu/",
        )

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["metric_name"] == "cpu"