from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from linux_server_monitoring_system.monitoring.api.views import ServerViewSet
from linux_server_monitoring_system.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("servers", ServerViewSet, basename="server")

app_name = "api"
urlpatterns = router.urls