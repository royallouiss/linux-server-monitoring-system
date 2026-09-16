from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from linux_server_monitoring_system.core.ssh import SSHService
from linux_server_monitoring_system.monitoring.jobs.monitoring import MonitoringJob
from linux_server_monitoring_system.monitoring.api.serializers import (
    MetricSampleSerializer,
)
from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Alert
from linux_server_monitoring_system.servers.models import Server

from .serializers import AlertSerializer
from .serializers import DashboardStatsSerializer
from .serializers import ServerSerializer
from .serializers import get_server_latest_metrics


def _calculate_fleet_averages(all_servers):
    cpu_list = []
    cpu_deltas = []
    mem_list = []
    mem_deltas = []
    disk_list = []
    for s in all_servers:
        metrics = get_server_latest_metrics(s)
        if metrics:
            cpu_list.append(metrics["cpu"]["usage_percent"])
            cpu_deltas.append(metrics["cpu"].get("delta", 0.0))
            mem_list.append(metrics["memory"]["usage_percent"])
            mem_deltas.append(metrics["memory"].get("delta", 0.0))
            disk_list.append(metrics["disk"]["usage_percent"])

    avg_cpu = round(sum(cpu_list) / len(cpu_list), 1) if cpu_list else 0.0
    avg_cpu_delta = (
        round(sum(cpu_deltas) / len(cpu_deltas), 2) if cpu_deltas else 0.0
    )
    avg_memory = round(sum(mem_list) / len(mem_list), 1) if mem_list else 0.0
    avg_memory_delta = (
        round(sum(mem_deltas) / len(mem_deltas), 2) if mem_deltas else 0.0
    )
    avg_disk = round(sum(disk_list) / len(disk_list), 1) if disk_list else 0.0

    return {
        "avg_cpu": avg_cpu,
        "avg_cpu_delta": avg_cpu_delta,
        "avg_memory": avg_memory,
        "avg_memory_delta": avg_memory_delta,
        "avg_disk": avg_disk,
    }


def _parse_activity_item(ts, sid, sinfo):
    m = sinfo["metrics"]
    cpu_v = m.get("cpu_usage", 0.0)
    mem_v = m.get("memory_usage", 0.0)
    disk_v = next(
        (v for k, v in m.items() if k.startswith("disk_usage:")),
        0.0,
    )
    rx_v = next(
        (
            round(v / 1024, 2)
            for k, v in m.items()
            if k.startswith("network_receive_rate:")
        ),
        0.0,
    )

    is_up = sinfo["status"] == "UP"
    return {
        "timestamp": ts.isoformat(),
        "server_id": sid,
        "server_name": sinfo["server_name"],
        "hostname": sinfo["hostname"],
        "status": sinfo["status"],
        "operation": "30s SSH Poll",
        "cpu_usage": round(cpu_v, 2),
        "memory_usage": round(mem_v, 2),
        "disk_usage": round(disk_v, 2),
        "network_rx_kbps": rx_v,
        "result": "Success (200 OK)" if is_up else "Failed",
        "message": (
            f"Polled CPU ({round(cpu_v, 2)}%), "
            f"RAM ({round(mem_v, 2)}%), "
            f"Disk ({round(disk_v, 2)}%)"
        ),
    }


def _annotate_activity_deltas(recent_activity):
    server_last_metrics = {}
    for item in reversed(recent_activity):
        sid = item["server_id"]
        if sid in server_last_metrics:
            prev = server_last_metrics[sid]
            item["cpu_delta"] = round(item["cpu_usage"] - prev["cpu_usage"], 2)
            item["mem_delta"] = round(item["memory_usage"] - prev["memory_usage"], 2)
        else:
            item["cpu_delta"] = 0.0
            item["mem_delta"] = 0.0
        server_last_metrics[sid] = item
    return recent_activity


def _build_recent_activity():
    recent_activity = []
    recent_timestamps = list(
        MetricSample.objects.values_list("timestamp", flat=True)
        .distinct()
        .order_by("-timestamp")[:15],
    )
    for ts in recent_timestamps:
        samples_at_ts = MetricSample.objects.filter(
            timestamp=ts,
        ).select_related("server")
        server_map = {}
        for sample in samples_at_ts:
            sid = sample.server_id
            if sid not in server_map:
                server_map[sid] = {
                    "server_name": sample.server.server_name,
                    "hostname": sample.server.hostname,
                    "status": sample.server.status,
                    "metrics": {},
                }
            server_map[sid]["metrics"][sample.metric_name] = float(sample.value)

        for sid, sinfo in server_map.items():
            recent_activity.append(_parse_activity_item(ts, sid, sinfo))

    return _annotate_activity_deltas(recent_activity)


class DashboardStatsView(APIView):
    """Provides high-level aggregated metrics for the monitoring dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: DashboardStatsSerializer})
    def get(self, request, *args, **kwargs):
        total_servers = Server.objects.count()
        online_servers = Server.objects.filter(status="UP").count()
        offline_servers = Server.objects.filter(status="DOWN").count()
        unknown_servers = Server.objects.filter(status="UNKNOWN").count()

        active_alerts = Alert.objects.filter(status=Alert.Status.ACTIVE).count()
        critical_alerts = Alert.objects.filter(
            status=Alert.Status.ACTIVE,
            severity=Alert.Severity.CRITICAL,
        ).count()
        warning_alerts = Alert.objects.filter(
            status=Alert.Status.ACTIVE,
            severity=Alert.Severity.WARNING,
        ).count()

        healthy_percent = (
            round((online_servers / total_servers) * 100, 1)
            if total_servers > 0
            else 0.0
        )

        fleet_averages = _calculate_fleet_averages(Server.objects.all())
        recent_activity = _build_recent_activity()

        data = {
            "total_servers": total_servers,
            "online_servers": online_servers,
            "offline_servers": offline_servers,
            "unknown_servers": unknown_servers,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "healthy_percent": healthy_percent,
            "avg_cpu": fleet_averages["avg_cpu"],
            "avg_cpu_delta": fleet_averages["avg_cpu_delta"],
            "avg_memory": fleet_averages["avg_memory"],
            "avg_memory_delta": fleet_averages["avg_memory_delta"],
            "avg_disk": fleet_averages["avg_disk"],
            "recent_activity": recent_activity,
            "last_updated": timezone.now(),
        }

        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)




class ServerViewSet(ModelViewSet):
    """ViewSet for managing servers, connection tests, and metrics."""

    queryset = (
        Server.objects.all()
        .prefetch_related("alerts", "metric_samples")
        .order_by("server_name")
    )
    serializer_class = ServerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search")
        status_param = self.request.query_params.get("status")

        if search:
            queryset = queryset.filter(
                server_name__icontains=search,
            ) | queryset.filter(hostname__icontains=search)
        if status_param and status_param.upper() in ["UP", "DOWN", "UNKNOWN"]:
            queryset = queryset.filter(status=status_param.upper())

        return queryset

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """Test SSH connectivity for a specific server and update its status."""
        server = self.get_object()
        ssh = SSHService()

        connected, message = ssh.connect(
            hostname=server.hostname,
            port=server.ssh_port,
            username=server.username,
            password=server.password,
        )

        check_time = timezone.now()

        if connected:
            cmd_ok, output = ssh.execute_command("hostname")
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
                ],
            )
            Alert.objects.filter(
                server=server,
                status=Alert.Status.ACTIVE,
                title="SSH Connection Failed",
            ).update(
                status=Alert.Status.RESOLVED,
                resolved_at=check_time,
                is_read=True,
            )
            Alert.objects.create(
                server=server,
                title="SSH Connection Successful",
                message=message or "SSH connection established successfully.",
                severity=Alert.Severity.INFO,
                status=Alert.Status.ACTIVE,
                is_read=False,
            )
            ssh.disconnect()

            return Response(
                {
                    "success": True,
                    "status": server.status,
                    "message": message,
                    "hostname": output if cmd_ok else "",
                    "last_check_at": server.last_check_at,
                },
                status=status.HTTP_200_OK,
            )

        server.status = "DOWN"
        server.last_check_at = check_time
        server.last_error = message
        server.save(update_fields=["status", "last_check_at", "last_error"])

        Alert.objects.create(
            server=server,
            title="SSH Connection Failed",
            message=message,
            severity=Alert.Severity.CRITICAL,
            status=Alert.Status.ACTIVE,
            is_read=False,
        )

        return Response(
            {
                "success": False,
                "status": server.status,
                "message": message,
                "last_check_at": server.last_check_at,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def collect_metrics(self, request, pk=None):
        """Triggers a fresh monitoring run for this server."""
        server = self.get_object()
        try:
            MonitoringJob.run(server)
            server.refresh_from_db()
            return Response(
                {
                    "success": True,
                    "message": "Metrics collected successfully.",
                    "server": ServerSerializer(server).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:  # noqa: BLE001

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def metrics(self, request, pk=None):
        """Returns time-series metric data for Chart.js visualization.

        Without a ``range`` query param, returns the raw serialized
        ``MetricSample`` list (monitoring API contract); with ``range``,
        returns the aggregated Chart.js series dict.
        """
        server = self.get_object()
        if "range" not in request.query_params:
            samples = MetricSample.objects.filter(server=server).order_by(
                "-timestamp",
            )
            return Response(
                MetricSampleSerializer(
                    samples,
                    many=True,
                    context={"request": request},
                ).data,
                status=status.HTTP_200_OK,
            )
        range_param = request.query_params.get("range", "24h").lower()

        now = timezone.now()
        ranges = {
            "1d": timedelta(days=1),
            "3d": timedelta(days=3),
            "1w": timedelta(days=7),
            "1m": timedelta(days=30),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }
        delta = ranges.get(range_param, timedelta(hours=24))
        since = now - delta

        samples = MetricSample.objects.filter(
            server=server, timestamp__gte=since,
        ).order_by("timestamp")

        # Fallback: if no samples in specific window, get latest samples up to 300
        if not samples.exists():
            distinct_times = (
                MetricSample.objects.filter(server=server)
                .values_list("timestamp", flat=True)
                .distinct()
                .order_by("-timestamp")[:50]
            )
            samples = MetricSample.objects.filter(
                server=server, timestamp__in=distinct_times,
            ).order_by("timestamp")

        # Group by timestamp
        grouped = {}
        for sample in samples:
            ts_key = sample.timestamp.isoformat()
            if ts_key not in grouped:
                grouped[ts_key] = {}
            grouped[ts_key][sample.metric_name] = float(sample.value)

        labels = []
        cpu_series = []
        load_1m_series = []
        mem_series = []
        disk_series = []
        net_rx_series = []
        net_tx_series = []

        for ts, metric_map in grouped.items():
            labels.append(ts)
            cpu_series.append(metric_map.get("cpu_usage", 0.0))
            load_1m_series.append(metric_map.get("load_1m", 0.0))
            mem_series.append(metric_map.get("memory_usage", 0.0))

            disk_val = 0.0
            for k, v in metric_map.items():
                if k.startswith("disk_usage:"):
                    disk_val = v
                    break
            disk_series.append(disk_val)

            rx_kb = 0.0
            tx_kb = 0.0
            for k, v in metric_map.items():
                if k.startswith("network_receive_rate:"):
                    rx_kb = round(v / 1024, 2)
                elif k.startswith("network_transmit_rate:"):
                    tx_kb = round(v / 1024, 2)
            net_rx_series.append(rx_kb)
            net_tx_series.append(tx_kb)

        latest_cpu_delta = (
            round(cpu_series[-1] - cpu_series[-2], 2)
            if len(cpu_series) > 1
            else 0.0
        )
        latest_mem_delta = (
            round(mem_series[-1] - mem_series[-2], 2)
            if len(mem_series) > 1
            else 0.0
        )
        latest_disk_delta = (
            round(disk_series[-1] - disk_series[-2], 2)
            if len(disk_series) > 1
            else 0.0
        )
        latest_rx_delta = (
            round(net_rx_series[-1] - net_rx_series[-2], 2)
            if len(net_rx_series) > 1
            else 0.0
        )
        latest_tx_delta = (
            round(net_tx_series[-1] - net_tx_series[-2], 2)
            if len(net_tx_series) > 1
            else 0.0
        )

        return Response(
            {
                "range": range_param,
                "server_id": server.id,
                "server_name": server.server_name,
                "labels": labels,
                "cpu": cpu_series,
                "load_1m": load_1m_series,
                "memory": mem_series,
                "disk": disk_series,
                "network_rx": net_rx_series,
                "network_tx": net_tx_series,
                "deltas": {
                    "cpu": latest_cpu_delta,
                    "memory": latest_mem_delta,
                    "disk": latest_disk_delta,
                    "network_rx": latest_rx_delta,
                    "network_tx": latest_tx_delta,
                },
                "interval_seconds": 30,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="fleet-metrics")
    def fleet_metrics(self, request):
        """Return time-series averages across all registered servers."""
        range_param = request.query_params.get("range", "24h").lower()
        ranges = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }
        since = timezone.now() - ranges.get(range_param, timedelta(hours=24))
        samples = MetricSample.objects.filter(
            timestamp__gte=since,
        ).order_by("timestamp")
        selected_server_ids = [
            value
            for value in request.query_params.get("server_ids", "").split(",")
            if value.isdigit()
        ]
        if selected_server_ids:
            samples = samples.filter(server_id__in=selected_server_ids)

        grouped = {}
        for sample in samples:
            timestamp_group = grouped.setdefault(sample.timestamp, {})
            server_metrics = timestamp_group.setdefault(sample.server_id, {})
            server_metrics[sample.metric_name] = float(sample.value)

        labels = []
        series = {
            "cpu": [],
            "load_1m": [],
            "memory": [],
            "disk": [],
            "network_rx": [],
            "network_tx": [],
        }
        for timestamp, server_maps in grouped.items():
            values = {key: [] for key in series}
            for metrics in server_maps.values():
                for key, metric_name in (
                    ("cpu", "cpu_usage"),
                    ("load_1m", "load_1m"),
                    ("memory", "memory_usage"),
                ):
                    if metric_name in metrics:
                        values[key].append(metrics[metric_name])

                for key, prefix, divisor in (
                    ("disk", "disk_usage:", 1),
                    ("network_rx", "network_receive_rate:", 1024),
                    ("network_tx", "network_transmit_rate:", 1024),
                ):
                    metric_value = next(
                        (
                            value / divisor
                            for name, value in metrics.items()
                            if name.startswith(prefix)
                        ),
                        None,
                    )
                    if metric_value is not None:
                        values[key].append(metric_value)

            labels.append(timestamp.isoformat())
            for key, values_for_metric in values.items():
                series[key].append(
                    round(sum(values_for_metric) / len(values_for_metric), 2)
                    if values_for_metric
                    else 0.0
                )

        def latest_delta(values):
            return round(values[-1] - values[-2], 2) if len(values) > 1 else 0.0

        return Response(
            {
                "range": range_param,
                "server_name": (
                    f"{len(selected_server_ids)} selected server(s)"
                    if selected_server_ids
                    else "All registered servers"
                ),
                "labels": labels,
                **series,
                "deltas": {
                    "cpu": latest_delta(series["cpu"]),
                    "memory": latest_delta(series["memory"]),
                    "disk": latest_delta(series["disk"]),
                    "network_rx": latest_delta(series["network_rx"]),
                    "network_tx": latest_delta(series["network_tx"]),
                },
                "interval_seconds": 30,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path=r"metrics/(?P<metric>[^/.]+)")
    def metric(self, request, pk=None, metric=None):
        """Returns raw serialized samples for a single metric name."""
        server = self.get_object()
        samples = MetricSample.objects.filter(
            server=server,
            metric_name=metric,
        ).order_by("-timestamp")
        return Response(
            MetricSampleSerializer(
                samples,
                many=True,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class AlertViewSet(ModelViewSet):
    """ViewSet for listing, filtering, and resolving alerts."""

    queryset = Alert.objects.all().select_related("server").order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        for server in Server.objects.filter(status="DOWN"):
            alert = (
                Alert.objects.filter(
                    server=server,
                    status=Alert.Status.ACTIVE,
                    severity=Alert.Severity.CRITICAL,
                    title="SSH Connection Failed",
                )
                .order_by("-created_at")
                .first()
            )
            if alert is None:
                Alert.objects.create(
                    server=server,
                    title="SSH Connection Failed",
                    message=server.last_error or "Server is currently offline.",
                    severity=Alert.Severity.CRITICAL,
                    status=Alert.Status.ACTIVE,
                    is_read=False,
                )
            elif alert.message != (server.last_error or "Server is currently offline."):
                alert.message = server.last_error or "Server is currently offline."
                alert.save(update_fields=["message"])

        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        severity_param = self.request.query_params.get("severity")
        server_param = self.request.query_params.get("server")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if severity_param:
            queryset = queryset.filter(severity=severity_param.upper())
        if server_param:
            queryset = queryset.filter(server_id=server_param)

        return queryset

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark an alert as resolved."""
        alert = self.get_object()
        alert.resolve()
        serializer = self.get_serializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        updated = self.get_queryset().filter(
            status=Alert.Status.ACTIVE,
            is_read=False,
        ).update(is_read=True)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
