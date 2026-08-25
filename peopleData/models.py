from django.db import models


class Person(models.Model):
    """A normalized person consolidated from one or more source records."""
    # Basic information
    name = models.CharField(max_length=255)

    email = models.EmailField(
        blank=True,
        null=True,
        db_index=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        db_index=True
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Source 1: Naukri Applicants
    experience_years = models.FloatField(
        blank=True,
        null=True
    )

    current_ctc = models.IntegerField(
        blank=True,
        null=True
    )

    applied_date = models.DateField(
        blank=True,
        null=True
    )

    skills = models.TextField(
        blank=True,
        null=True
    )

    # Source 2: Gig Workers
    rate = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # Source 3: CB Nexus Contacts
    verified = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    projects_completed = models.IntegerField(
        blank=True,
        null=True
    )

    source_summary = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ("name", "id")

    def __str__(self):
        return self.name


class PersonSourceRecord(models.Model):
    """Immutable provenance for a normalized row used to construct a person."""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="source_records")
    source = models.CharField(max_length=30)
    source_row = models.PositiveIntegerField()
    raw_data = models.JSONField()
    normalized_data = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=("source", "source_row"), name="unique_import_source_row")]


class ImportIssue(models.Model):
    """A source row excluded from import, retained with its rejection reason."""
    source = models.CharField(max_length=30)
    source_row = models.PositiveIntegerField()
    issue_type = models.CharField(max_length=40)
    detail = models.TextField()
    raw_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
