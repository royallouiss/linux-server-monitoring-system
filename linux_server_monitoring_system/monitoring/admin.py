from django.contrib import admin
from django.utils.html import format_html

from .models import MetricSample


@admin.register(MetricSample)
class MetricSampleAdmin(admin.ModelAdmin):
    list_display = (
        "server",
        "metric_name",
        "formatted_value",
        "unit",
        "timestamp",
    )

    list_filter = (
        "metric_name",
        "unit",
        "server",
    )

    search_fields = (
        "server__server_name",
        "server__hostname",
        "metric_name",
    )

    date_hierarchy = "timestamp"

    ordering = (
        "-timestamp",
    )

    readonly_fields = (
        "server",
        "metric_name",
        "value",
        "unit",
        "timestamp",
    )

    @admin.display(description="Value", ordering="value")
    def formatted_value(self, obj):
        return format_html(
            '<span class="badge-metric-value">{}</span>',
            obj.value,
        )

    def has_add_permission(self, request):
        # Automated telemetry samples are ingested by background collectors
        return False

    def has_change_permission(self, request, obj=None):
        return False
