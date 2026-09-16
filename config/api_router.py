from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from linux_server_monitoring_system.monitoring.api.views import (
    ServerViewSet as MonitoringServerViewSet,
)
from linux_server_monitoring_system.servers.api.views import AlertViewSet
from linux_server_monitoring_system.servers.api.views import DashboardStatsView
from linux_server_monitoring_system.servers.api.views import ServerViewSet
from linux_server_monitoring_system.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
# The servers app viewset implements the dashboard contract (metrics chart
# series, test_connection, collect_metrics); it also serves the monitoring
# API's raw sample list and per-metric endpoints via its metrics actions.
router.register("servers", ServerViewSet, basename="server")
router.register("alerts", AlertViewSet)
# Kept accessible for the monitoring API serializers/tests that only need
# read-only sample listing without the dashboard aggregation.
router.register(
    "monitoring/servers",
    MonitoringServerViewSet,
    basename="monitoring-server",
)

app_name = "api"
urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    *router.urls,
]