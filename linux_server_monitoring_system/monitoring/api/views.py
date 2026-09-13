from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Server

from .serializers import MetricSampleSerializer
from .serializers import ServerSerializer


class ServerViewSet(ReadOnlyModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer
    lookup_field = "pk"

    @action(detail=True, methods=["get"], url_path="metrics")
    def metrics(self, request, pk=None):
        server = self.get_object()
        metrics = MetricSample.objects.filter(server=server).order_by("-timestamp")

        serializer = MetricSampleSerializer(
            metrics,
            many=True,
            context={"request": request},
        )

        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"metrics/(?P<metric>[^/.]+)",
    )
    def metric(self, request, pk=None, metric=None):
        server = self.get_object()

        metrics = MetricSample.objects.filter(
            server=server,
            metric_name=metric,
        ).order_by("-timestamp")

        serializer = MetricSampleSerializer(
            metrics,
            many=True,
            context={"request": request},
        )

        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )