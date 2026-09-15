from decimal import Decimal, InvalidOperation

from django.db import transaction

from linux_server_monitoring_system.monitoring.models import MetricSample
from linux_server_monitoring_system.servers.models import Alert
from linux_server_monitoring_system.servers.models import AlertRule
from linux_server_monitoring_system.servers.models import Server

from .notifications import NotificationService


class AlertEvaluator:
    def __init__(self, notification_service=None):
        self.notification_service = notification_service or NotificationService()

    def evaluate_server(self, server):
        alerts = []
        rules = AlertRule.objects.filter(enabled=True).filter(
            server__isnull=True,
        ) | AlertRule.objects.filter(enabled=True, server=server)

        for rule in rules:
            violated = self._is_violated(server, rule)
            alert = self._apply_rule(server, rule, violated)
            if alert is not None:
                alerts.append(alert)

        return alerts

    def _is_violated(self, server, rule):
        if rule.metric_name == "server_status":
            value = server.status
        else:
            sample = (
                MetricSample.objects.filter(
                    server=server,
                    metric_name=rule.metric_name,
                )
                .order_by("-timestamp", "-id")
                .first()
            )
            if sample is None:
                return False
            value = sample.value

        return self._compare(value, rule.operator, rule.threshold)

    @staticmethod
    def _compare(value, operator, threshold):
        if isinstance(value, str):
            left = value.upper()
            right = threshold.upper()
        else:
            try:
                left = Decimal(str(value))
                right = Decimal(threshold)
            except (InvalidOperation, TypeError):
                return False

        return {
            AlertRule.Operator.GREATER_THAN: left > right,
            AlertRule.Operator.GREATER_THAN_OR_EQUAL: left >= right,
            AlertRule.Operator.LESS_THAN: left < right,
            AlertRule.Operator.LESS_THAN_OR_EQUAL: left <= right,
            AlertRule.Operator.EQUAL: left == right,
            AlertRule.Operator.NOT_EQUAL: left != right,
        }[operator]

    @transaction.atomic
    def _apply_rule(self, server, rule, violated):
        active_statuses = [Alert.Status.ACTIVE, Alert.Status.ACKNOWLEDGED]
        active_alert = (
            Alert.objects.select_for_update()
            .filter(
                server=server,
                rule=rule,
                status__in=active_statuses,
            )
            .first()
        )

        if violated:
            if active_alert is not None:
                return None

            alert = Alert.objects.create(
                server=server,
                rule=rule,
                metric_name=rule.metric_name,
                title=f"{rule.metric_name} threshold violated",
                message=(
                    f"{server.server_name}: {rule.metric_name} "
                    f"{rule.operator} {rule.threshold}."
                ),
                severity=rule.severity,
            )
            self.notification_service.notify(alert)
            return alert

        if active_alert is not None:
            active_alert.resolve()

        return None


def evaluate_server(server):
    return AlertEvaluator().evaluate_server(
        server if isinstance(server, Server) else Server.objects.get(pk=server),
    )
