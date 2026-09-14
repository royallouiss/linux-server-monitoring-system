"""Template tags for server monitoring administration dashboard."""

from django import template

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Alert
from linux_server_monitoring_system.servers.models import Server

register = template.Library()


@register.simple_tag
def get_admin_monitoring_stats():
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

    total_metrics = MetricSample.objects.count()

    health_pct = (
        round((online_servers / total_servers) * 100, 1)
        if total_servers > 0
        else 100.0
    )

    servers = list(Server.objects.all().order_by("server_name")[:8])
    recent_alerts = list(
        Alert.objects.select_related("server").order_by("-created_at")[:6],
    )

    return {
        "total_servers": total_servers,
        "online_servers": online_servers,
        "offline_servers": offline_servers,
        "unknown_servers": unknown_servers,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "warning_alerts": warning_alerts,
        "total_metrics": total_metrics,
        "health_pct": health_pct,
        "servers": servers,
        "recent_alerts": recent_alerts,
    }
