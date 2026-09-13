from rest_framework import serializers

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Server


class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = [
            "id",
            "server_name",
            "hostname",
            "ssh_port",
            "username",
            "operating_system",
            "description",
            "is_active",
            "status",
            "last_check_at",
            "last_success_at",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "last_check_at",
            "last_success_at",
            "last_error",
            "created_at",
            "updated_at",
        ]


class MetricSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricSample
        fields = [
            "id",
            "server",
            "metric_name",
            "value",
            "unit",
            "timestamp",
        ]
        read_only_fields = ["id"]