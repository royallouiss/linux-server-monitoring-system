from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0003_alert"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE servers_alert "
                "ADD COLUMN IF NOT EXISTS metric_name varchar(255) "
                "NOT NULL DEFAULT '';"
                "ALTER TABLE servers_alert "
                "ALTER COLUMN metric_name SET DEFAULT '';"
                "UPDATE servers_alert SET metric_name = '' "
                "WHERE metric_name IS NULL;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
