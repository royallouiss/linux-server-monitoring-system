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


def _get_server_warning_status(server):
    if server.status == "DOWN":
        return False
    if server.alerts.filter(
        status=Alert.Status.ACTIVE,
        severity__in=[Alert.Severity.WARNING, Alert.Severity.CRITICAL],
    ).exists():
        return True
    m = get_server_latest_metrics(server)
    if m:
        c = m.get("cpu", {}).get("usage_percent", 0.0)
        mem = m.get("memory", {}).get("usage_percent", 0.0)
        d = m.get("disk", {}).get("usage_percent", 0.0)
        if c >= 80 or mem >= 80 or d >= 80:
            return True
    return False


def _build_monitoring_engine_status(all_servers):
    total_metrics_count = MetricSample.objects.count()
    last_success = None
    last_fail = None
    last_check = None

    for s in all_servers:
        if s.last_check_at and (last_check is None or s.last_check_at > last_check):
            last_check = s.last_check_at
        if s.last_success_at and (last_success is None or s.last_success_at > last_success):
            last_success = s.last_success_at
        if s.last_error and s.last_check_at and (last_fail is None or s.last_check_at > last_fail):
            last_fail = s.last_check_at

    has_active_servers = any(s.is_active for s in all_servers)
    has_recent_failures = any(s.status == "DOWN" or bool(s.last_error) for s in all_servers)

    return {
        "service_status": "Running" if has_active_servers else "Standby",
        "scheduler_status": "Active" if has_active_servers else "Idle",
        "runner_status": "Degraded" if has_recent_failures else "Healthy",
        "last_successful_run": last_success.isoformat() if last_success else None,
        "last_failed_run": last_fail.isoformat() if last_fail else None,
        "last_check": last_check.isoformat() if last_check else None,
        "total_metrics_count": total_metrics_count,
    }


def _build_operational_tasks(all_servers):
    tasks = []
    # 1. Offline servers (URGENT)
    for s in all_servers:
        if s.status == "DOWN":
            err_snip = f": {s.last_error[:50]}..." if s.last_error else ""
            tasks.append({
                "id": f"task-offline-{s.id}",
                "priority": "URGENT",
                "server_id": s.id,
                "server_name": s.server_name,
                "hostname": s.hostname,
                "title": f"Server Offline - Connection unreachable{err_snip}",
                "action_type": "test_ssh",
                "action_label": "Test SSH",
            })

    # 2. Critical alerts (URGENT / HIGH)
    crit_alerts = Alert.objects.filter(
        status=Alert.Status.ACTIVE,
        severity=Alert.Severity.CRITICAL,
    ).select_related("server")
    for a in crit_alerts:
        tasks.append({
            "id": f"task-alert-{a.id}",
            "priority": "URGENT",
            "server_id": a.server_id,
            "server_name": a.server.server_name,
            "hostname": a.server.hostname,
            "title": f"Critical Incident: {a.title}",
            "action_type": "view_details",
            "action_label": "Investigate",
        })

    # 3. Warning alerts & High resource thresholds (HIGH)
    warn_alerts = Alert.objects.filter(
        status=Alert.Status.ACTIVE,
        severity=Alert.Severity.WARNING,
    ).select_related("server")
    for a in warn_alerts:
        tasks.append({
            "id": f"task-alert-{a.id}",
            "priority": "HIGH",
            "server_id": a.server_id,
            "server_name": a.server.server_name,
            "hostname": a.server.hostname,
            "title": f"Warning Alert: {a.title}",
            "action_type": "view_details",
            "action_label": "Review Alert",
        })

    for s in all_servers:
        if s.status == "UP":
            m = get_server_latest_metrics(s)
            if m:
                cpu_v = m.get("cpu", {}).get("usage_percent", 0.0)
                mem_v = m.get("memory", {}).get("usage_percent", 0.0)
                disk_v = m.get("disk", {}).get("usage_percent", 0.0)
                if disk_v >= 85:
                    tasks.append({
                        "id": f"task-disk-{s.id}",
                        "priority": "HIGH",
                        "server_id": s.id,
                        "server_name": s.server_name,
                        "hostname": s.hostname,
                        "title": f"High Disk Utilization ({disk_v}%) on {m.get('disk', {}).get('mount_point', '/')}",
                        "action_type": "view_details",
                        "action_label": "Inspect Disk",
                    })
                elif cpu_v >= 85:
                    tasks.append({
                        "id": f"task-cpu-{s.id}",
                        "priority": "HIGH",
                        "server_id": s.id,
                        "server_name": s.server_name,
                        "hostname": s.hostname,
                        "title": f"Elevated CPU Utilization ({cpu_v}%)",
                        "action_type": "view_details",
                        "action_label": "Inspect CPU",
                    })
                elif mem_v >= 85:
                    tasks.append({
                        "id": f"task-mem-{s.id}",
                        "priority": "HIGH",
                        "server_id": s.id,
                        "server_name": s.server_name,
                        "hostname": s.hostname,
                        "title": f"Elevated Memory Usage ({mem_v}%)",
                        "action_type": "view_details",
                        "action_label": "Inspect RAM",
                    })

    # 4. Monitoring errors / unknown status (MEDIUM)
    for s in all_servers:
        if s.status == "UNKNOWN":
            tasks.append({
                "id": f"task-unknown-{s.id}",
                "priority": "MEDIUM",
                "server_id": s.id,
                "server_name": s.server_name,
                "hostname": s.hostname,
                "title": f"No telemetry recorded yet - initial check pending",
                "action_type": "collect_metrics",
                "action_label": "Collect Now",
            })
        elif s.last_error and s.status != "DOWN":
            tasks.append({
                "id": f"task-err-{s.id}",
                "priority": "MEDIUM",
                "server_id": s.id,
                "server_name": s.server_name,
                "hostname": s.hostname,
                "title": f"Recent check warning: {s.last_error[:50]}",
                "action_type": "collect_metrics",
                "action_label": "Retry Run",
            })

    # 5. Fallback INFO task if everything is green
    if not tasks:
        tasks.append({
            "id": "task-info-fleet-healthy",
            "priority": "INFO",
            "server_id": all_servers[0].id if all_servers else None,
            "server_name": "Fleet",
            "hostname": "All servers",
            "title": "All systems operating normally — no pending operational issues",
            "action_type": "none",
            "action_label": "Fleet Healthy",
        })

    return tasks[:8]


def _build_resource_sparklines():
    recent_ts = list(
        MetricSample.objects.values_list("timestamp", flat=True)
        .distinct()
        .order_by("-timestamp")[:10]
    )
    recent_ts.reverse()

    cpu_pts = []
    mem_pts = []
    disk_pts = []
    net_pts = []

    for ts in recent_ts:
        samples = MetricSample.objects.filter(timestamp=ts)
        cpu_vals = [float(s.value) for s in samples if s.metric_name == "cpu_usage"]
        mem_vals = [float(s.value) for s in samples if s.metric_name == "memory_usage"]
        disk_vals = [float(s.value) for s in samples if s.metric_name.startswith("disk_usage:")]
        rx_vals = [float(s.value) / 1024 for s in samples if s.metric_name.startswith("network_receive_rate:")]

        if cpu_vals:
            cpu_pts.append(round(sum(cpu_vals) / len(cpu_vals), 1))
        if mem_vals:
            mem_pts.append(round(sum(mem_vals) / len(mem_vals), 1))
        if disk_vals:
            disk_pts.append(round(sum(disk_vals) / len(disk_vals), 1))
        if rx_vals:
            net_pts.append(round(sum(rx_vals) / len(rx_vals), 1))

    return {
        "cpu": cpu_pts,
        "memory": mem_pts,
        "disk": disk_pts,
        "network": net_pts,
    }


class DashboardStatsView(APIView):
    """Provides high-level aggregated metrics for the monitoring dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: DashboardStatsSerializer})
    def get(self, request, *args, **kwargs):
        all_servers = list(Server.objects.all().prefetch_related("alerts", "metric_samples"))
        total_servers = len(all_servers)
        online_servers = sum(1 for s in all_servers if s.status == "UP")
        offline_servers = sum(1 for s in all_servers if s.status == "DOWN")
        unknown_servers = sum(1 for s in all_servers if s.status == "UNKNOWN")
        warning_servers = sum(1 for s in all_servers if _get_server_warning_status(s))

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

        active_servers_count = sum(1 for s in all_servers if s.is_active)
        if active_servers_count > 0:
            monitoring_success_rate = round((online_servers / active_servers_count) * 100, 1)
        elif total_servers > 0:
            monitoring_success_rate = round((online_servers / total_servers) * 100, 1)
        else:
            monitoring_success_rate = 100.0

        if offline_servers > 0 or critical_alerts > 0:
            system_status = "CRITICAL"
        elif warning_servers > 0 or warning_alerts > 0:
            system_status = "WARNING"
        else:
            system_status = "HEALTHY"

        fleet_averages = _calculate_fleet_averages(all_servers)
        recent_activity = _build_recent_activity()
        monitoring_engine = _build_monitoring_engine_status(all_servers)
        tasks = _build_operational_tasks(all_servers)
        resource_sparklines = _build_resource_sparklines()

        data = {
            "total_servers": total_servers,
            "online_servers": online_servers,
            "warning_servers": warning_servers,
            "offline_servers": offline_servers,
            "unknown_servers": unknown_servers,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "healthy_percent": healthy_percent,
            "monitoring_success_rate": monitoring_success_rate,
            "system_status": system_status,
            "avg_cpu": fleet_averages["avg_cpu"],
            "avg_cpu_delta": fleet_averages["avg_cpu_delta"],
            "avg_memory": fleet_averages["avg_memory"],
            "avg_memory_delta": fleet_averages["avg_memory_delta"],
            "avg_disk": fleet_averages["avg_disk"],
            "monitoring_engine": monitoring_engine,
            "tasks": tasks,
            "resource_sparklines": resource_sparklines,
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

        # Create active alert if one doesn't exist
        Alert.objects.get_or_create(
            server=server,
            status=Alert.Status.ACTIVE,
            severity=Alert.Severity.CRITICAL,
            title="SSH Connection Failed",
            defaults={"message": message},
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
        """Returns time-series metric data for Chart.js visualization."""
        server = self.get_object()
        range_param = request.query_params.get("range", "24h").lower()

        now = timezone.now()
        ranges = {
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

        def _calc_stats(series):
            if not series:
                return {"current": 0.0, "avg": 0.0, "peak": 0.0}
            return {
                "current": round(series[-1], 2),
                "avg": round(sum(series) / len(series), 2),
                "peak": round(max(series), 2),
            }

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
                "summary": {
                    "cpu": _calc_stats(cpu_series),
                    "memory": _calc_stats(mem_series),
                    "disk": _calc_stats(disk_series),
                    "network_rx": _calc_stats(net_rx_series),
                    "network_tx": _calc_stats(net_tx_series),
                },
                "interval_seconds": 10,
            },
            status=status.HTTP_200_OK,
        )



class AlertViewSet(ModelViewSet):
    """ViewSet for listing, filtering, and resolving alerts."""

    queryset = Alert.objects.all().select_related("server").order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
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
