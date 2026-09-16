from rest_framework import serializers

from linux_server_monitoring_system.servers.models import Alert
from linux_server_monitoring_system.servers.models import Server


def _parse_disk_metrics(sample_dict):
    disk_usage = 0.0
    disk_used = 0
    disk_avail = 0
    disk_mount = "/"
    for key, val in sample_dict.items():
        if key.startswith("disk_usage:"):
            disk_usage = val
            disk_mount = key.split(":", 1)[1]
        elif key.startswith("disk_used:"):
            disk_used = int(val)
        elif key.startswith("disk_available:"):
            disk_avail = int(val)
    return {
        "mount_point": disk_mount,
        "usage_percent": round(disk_usage, 2),
        "used_bytes": disk_used,
        "available_bytes": disk_avail,
        "used_gb": round(disk_used / (1024**3), 2),
        "total_gb": round((disk_used + disk_avail) / (1024**3), 2),
    }


def _parse_network_metrics(sample_dict):
    net_rx_rate = 0.0
    net_tx_rate = 0.0
    net_rx_bytes = 0
    net_tx_bytes = 0
    net_iface = "eth0"
    for key, val in sample_dict.items():
        if key.startswith("network_receive_rate:"):
            net_rx_rate = val
            net_iface = key.split(":", 1)[1]
        elif key.startswith("network_transmit_rate:"):
            net_tx_rate = val
        elif key.startswith("network_received_bytes:"):
            net_rx_bytes = int(val)
        elif key.startswith("network_transmitted_bytes:"):
            net_tx_bytes = int(val)
    return {
        "interface": net_iface,
        "receive_rate": round(net_rx_rate, 2),
        "transmit_rate": round(net_tx_rate, 2),
        "receive_rate_kbps": round(net_rx_rate / 1024, 2),
        "transmit_rate_kbps": round(net_tx_rate / 1024, 2),
        "received_bytes": net_rx_bytes,
        "transmitted_bytes": net_tx_bytes,
    }


def _calculate_deltas(sample_dict, prev_dict):
    cpu_usage = sample_dict.get("cpu_usage", 0.0)
    prev_cpu = prev_dict.get("cpu_usage", cpu_usage)
    cpu_delta = round(cpu_usage - prev_cpu, 2)

    mem_usage = sample_dict.get("memory_usage", 0.0)
    prev_mem = prev_dict.get("memory_usage", mem_usage)
    mem_delta = round(mem_usage - prev_mem, 2)

    return {
        "cpu_usage": round(cpu_usage, 2),
        "cpu_delta": cpu_delta,
        "mem_usage": round(mem_usage, 2),
        "mem_delta": mem_delta,
    }


def get_server_latest_metrics(server):
    distinct_times = list(
        server.metric_samples.values_list("timestamp", flat=True)
        .distinct()
        .order_by("-timestamp")[:2],
    )

    if not distinct_times:
        return None

    latest_time = distinct_times[0]
    samples = server.metric_samples.filter(timestamp=latest_time)
    sample_dict = {s.metric_name: float(s.value) for s in samples}

    prev_dict = {}
    interval_sec = 30
    if len(distinct_times) > 1:
        prev_time = distinct_times[1]
        prev_samples = server.metric_samples.filter(timestamp=prev_time)
        prev_dict = {s.metric_name: float(s.value) for s in prev_samples}
        interval_sec = max(1, int((latest_time - prev_time).total_seconds()))

    deltas = _calculate_deltas(sample_dict, prev_dict)

    mem_used = int(sample_dict.get("memory_used", 0))
    mem_avail = int(sample_dict.get("memory_available", 0))

    disk_data = _parse_disk_metrics(sample_dict)
    prev_disk = _parse_disk_metrics(prev_dict) if prev_dict else disk_data
    disk_data["delta"] = round(
        disk_data["usage_percent"] - prev_disk["usage_percent"],
        2,
    )

    net_data = _parse_network_metrics(sample_dict)
    prev_net = _parse_network_metrics(prev_dict) if prev_dict else net_data
    net_data["rx_delta_kbps"] = round(
        net_data["receive_rate_kbps"] - prev_net["receive_rate_kbps"],
        2,
    )
    net_data["tx_delta_kbps"] = round(
        net_data["transmit_rate_kbps"] - prev_net["transmit_rate_kbps"],
        2,
    )

    return {
        "timestamp": latest_time.isoformat(),
        "interval_seconds": interval_sec,
        "cpu": {
            "usage_percent": deltas["cpu_usage"],
            "delta": deltas["cpu_delta"],
            "load_1m": round(sample_dict.get("load_1m", 0.0), 2),
            "load_5m": round(sample_dict.get("load_5m", 0.0), 2),
            "load_15m": round(sample_dict.get("load_15m", 0.0), 2),
        },
        "memory": {
            "usage_percent": deltas["mem_usage"],
            "delta": deltas["mem_delta"],
            "used_bytes": mem_used,
            "available_bytes": mem_avail,
            "used_gb": round(mem_used / (1024**3), 2),
            "total_gb": round((mem_used + mem_avail) / (1024**3), 2),
        },
        "disk": disk_data,
        "network": net_data,
    }




class AlertSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(
        source="server.server_name",
        read_only=True,
    )
    server_hostname = serializers.CharField(
        source="server.hostname",
        read_only=True,
    )
    severity_display = serializers.CharField(
        source="get_severity_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "server",
            "server_name",
            "server_hostname",
            "title",
            "message",
            "severity",
            "severity_display",
            "status",
            "is_read",
            "status_display",
            "created_at",
            "resolved_at",
        ]


class ServerSerializer(serializers.ModelSerializer):
    operating_system_display = serializers.CharField(
        source="get_operating_system_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    active_alerts_count = serializers.SerializerMethodField()
    latest_metrics = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = [
            "id",
            "server_name",
            "hostname",
            "ssh_port",
            "username",
            "password",
            "operating_system",
            "operating_system_display",
            "status",
            "status_display",
            "last_check_at",
            "last_success_at",
            "last_error",
            "description",
            "is_active",
            "active_alerts_count",
            "latest_metrics",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": False,
            },
        }

    def get_active_alerts_count(self, obj: Server) -> int:
        return obj.alerts.filter(status=Alert.Status.ACTIVE).count()

    def get_latest_metrics(self, obj: Server):
        return get_server_latest_metrics(obj)


class DashboardStatsSerializer(serializers.Serializer):
    total_servers = serializers.IntegerField()
    online_servers = serializers.IntegerField()
    offline_servers = serializers.IntegerField()
    unknown_servers = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    warning_alerts = serializers.IntegerField()
    healthy_percent = serializers.FloatField()
    avg_cpu = serializers.FloatField()
    avg_cpu_delta = serializers.FloatField(default=0.0)
    avg_memory = serializers.FloatField()
    avg_memory_delta = serializers.FloatField(default=0.0)
    avg_disk = serializers.FloatField()
    recent_activity = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    last_updated = serializers.DateTimeField()

