import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("peopleData", "0002_import_audit")]

    operations = [
        migrations.CreateModel(
            name="AudioSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audio_file", models.FileField(upload_to="audio_submissions/%Y/%m/%d/")),
                ("original_filename", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audio_submissions", to="peopleData.person")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
