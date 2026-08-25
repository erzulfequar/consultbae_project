from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("peopleData", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="person", name="source_summary", field=models.CharField(blank=True, max_length=100),
        ),
        migrations.CreateModel(
            name="ImportIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=30)),
                ("source_row", models.PositiveIntegerField()),
                ("issue_type", models.CharField(max_length=40)),
                ("detail", models.TextField()),
                ("raw_data", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="PersonSourceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=30)),
                ("source_row", models.PositiveIntegerField()),
                ("raw_data", models.JSONField()),
                ("normalized_data", models.JSONField()),
                ("person", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="source_records", to="peopleData.person")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("source", "source_row"), name="unique_import_source_row")]},
        ),
    ]
