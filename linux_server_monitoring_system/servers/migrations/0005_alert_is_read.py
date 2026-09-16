from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0004_alert_metric_name_compat"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
    ]
