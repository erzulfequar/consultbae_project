from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audio", "0001_initial")]
    operations = [
        migrations.AddField(model_name="audiosubmission", name="bitrate_kbps", field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name="audiosubmission", name="channels", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="audiosubmission", name="content_type", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="audiosubmission", name="duration_seconds", field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name="audiosubmission", name="file_size_bytes", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="audiosubmission", name="noise_floor_dbfs", field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name="audiosubmission", name="sample_rate_hz", field=models.PositiveIntegerField(blank=True, null=True)),
    ]
