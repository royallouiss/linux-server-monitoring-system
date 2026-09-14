from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from linux_server_monitoring_system.servers.api.views import AlertViewSet
from linux_server_monitoring_system.servers.api.views import DashboardStatsView
from linux_server_monitoring_system.servers.api.views import ServerViewSet
from linux_server_monitoring_system.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("servers", ServerViewSet)
router.register("alerts", AlertViewSet)

app_name = "api"
urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    *router.urls,
]

