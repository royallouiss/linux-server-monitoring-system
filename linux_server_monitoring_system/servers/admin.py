from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html

from linux_server_monitoring_system.core.ssh import SSHService

from .models import Alert
from .models import Server


class ServerAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=True,
        help_text=(
            "Stored securely for SSH authentication and "
            "monitoring telemetry collection."
        ),
    )

    class Meta:
        model = Server
        fields = [
            "server_name",
            "hostname",
            "ssh_port",
            "username",
            "password",
            "operating_system",
            "description",
            "is_active",
            "status",
        ]


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    form = ServerAdminForm

    list_display = (
        "server_name",
        "hostname",
        "status_badge",
        "os_badge",
        "username",
        "ssh_port",
        "is_active",
        "last_check_at",
        "created_at",
    )

    search_fields = (
        "server_name",
        "hostname",
        "username",
    )

    list_filter = (
        "status",
        "operating_system",
        "is_active",
    )

    ordering = (
        "server_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_check_at",
        "last_success_at",
    )

    fieldsets = (
        (
            "Server Identity",
            {
                "fields": (
                    "server_name",
                    "hostname",
                    "description",
                    "is_active",
                ),
            },
        ),
        (
            "SSH Credentials & Access",
            {
                "fields": (
                    "username",
                    "ssh_port",
                    "password",
                ),
                "description": (
                    "Credentials are used by SSH workers to poll system telemetry."
                ),
            },
        ),
        (
            "Health & Telemetry Status",
            {
                "fields": (
                    "status",
                    "operating_system",
                    "last_check_at",
                    "last_success_at",
                    "last_error",
                ),
            },
        ),
        (
            "Audit Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["test_ssh_connectivity"]

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status_classes = {
            "UP": "badge-admin-up",
            "DOWN": "badge-admin-down",
            "UNKNOWN": "badge-admin-unknown",
        }
        dot_classes = {
            "UP": "badge-dot-up",
            "DOWN": "badge-dot-down",
            "UNKNOWN": "badge-dot-unknown",
        }
        css_class = status_classes.get(obj.status, "badge-admin-unknown")
        dot_class = dot_classes.get(obj.status, "badge-dot-unknown")
        return format_html(
            '<span class="badge-admin-status {}">'
            '<span class="badge-dot {}"></span>{}</span>',
            css_class,
            dot_class,
            obj.get_status_display(),
        )

    @admin.display(description="OS", ordering="operating_system")
    def os_badge(self, obj):
        os_lower = (obj.operating_system or "").lower()
        if "ubuntu" in os_lower:
            os_cls = "badge-os-ubuntu"
        elif "debian" in os_lower:
            os_cls = "badge-os-debian"
        else:
            os_cls = ""
        return format_html(
            '<span class="badge-os {}">{}</span>',
            os_cls,
            obj.operating_system or "Linux",
        )

    @admin.action(description="Test SSH connectivity for selected servers")
    def test_ssh_connectivity(self, request, queryset):
        success_count = 0
        fail_count = 0
        now = timezone.now()
        for server in queryset:
            ssh = SSHService()
            success, msg = ssh.connect(
                hostname=server.hostname,
                port=server.ssh_port,
                username=server.username,
                password=server.password,
            )
            server.last_check_at = now
            if success:
                server.status = "UP"
                server.last_success_at = now
                server.last_error = ""
                ssh.disconnect()
                success_count += 1
            else:
                server.status = "DOWN"
                server.last_error = msg
                fail_count += 1
            server.save(
                update_fields=[
                    "status",
                    "last_check_at",
                    "last_success_at",
                    "last_error",
                ],
            )

        if success_count:
            self.message_user(
                request,
                f"Successfully connected to {success_count} server(s).",
                level=messages.SUCCESS,
            )
        if fail_count:
            self.message_user(
                request,
                f"Connection failed for {fail_count} server(s).",
                level=messages.ERROR,
            )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "server",
        "title",
        "severity_badge",
        "status_badge",
        "created_at",
        "resolved_at",
    )

    search_fields = (
        "server__server_name",
        "title",
        "message",
    )

    list_filter = (
        "severity",
        "status",
        "created_at",
    )

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
    )

    actions = ["mark_resolved", "mark_active"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Severity", ordering="severity")
    def severity_badge(self, obj):
        classes = {
            Alert.Severity.CRITICAL: "badge-admin-critical",
            Alert.Severity.WARNING: "badge-admin-warning",
            Alert.Severity.INFO: "badge-admin-info",
        }
        cls = classes.get(obj.severity, "badge-admin-info")
        return format_html(
            '<span class="badge-admin-status {}">{}</span>',
            cls,
            obj.get_severity_display(),
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        cls = (
            "badge-admin-active"
            if obj.status == Alert.Status.ACTIVE
            else "badge-admin-resolved"
        )
        return format_html(
            '<span class="badge-admin-status {}">{}</span>',
            cls,
            obj.get_status_display(),
        )

    @admin.action(description="Mark selected alerts as RESOLVED")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(
            status=Alert.Status.RESOLVED,
            resolved_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Marked {updated} alert(s) as RESOLVED.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Mark selected alerts as ACTIVE")
    def mark_active(self, request, queryset):
        updated = queryset.update(
            status=Alert.Status.ACTIVE,
            resolved_at=None,
        )
        self.message_user(
            request,
            f"Marked {updated} alert(s) as ACTIVE.",
            level=messages.INFO,
        )
