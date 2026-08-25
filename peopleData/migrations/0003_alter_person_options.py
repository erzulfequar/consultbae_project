from django.db import migrations


class Migration(migrations.Migration):
    """Persist the deterministic ordering declared on the Person model."""

    dependencies = [("peopleData", "0002_import_audit")]

    operations = [
        migrations.AlterModelOptions(
            name="person",
            options={"ordering": ("name", "id")},
        ),
    ]
