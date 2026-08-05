from django import forms
from django.contrib import admin

from .models import Server


class ServerAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=True,
    )

    class Meta:
        model = Server
        fields = "__all__"


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    form = ServerAdminForm

    list_display = (
        "server_name",
        "hostname",
        "operating_system",
        "username",
        "ssh_port",
        "is_active",
        "created_at",
    )

    search_fields = (
        "server_name",
        "hostname",
        "username",
    )

    list_filter = (
        "operating_system",
        "is_active",
    )

    ordering = (
        "server_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )