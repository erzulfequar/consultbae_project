from django.contrib import admin

from .models import ImportIssue, Person, PersonSourceRecord


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Make consolidated people easy to search during review."""

    list_display = ("name", "email", "phone", "city", "source_summary")
    search_fields = ("name", "email", "phone", "city")
    list_filter = ("city", "source_summary")


@admin.register(PersonSourceRecord)
class PersonSourceRecordAdmin(admin.ModelAdmin):
    """Expose source-level provenance without allowing accidental edits."""

    list_display = ("person", "source", "source_row")
    list_filter = ("source",)
    search_fields = ("person__name",)
    readonly_fields = ("person", "source", "source_row", "raw_data", "normalized_data")


@admin.register(ImportIssue)
class ImportIssueAdmin(admin.ModelAdmin):
    """Show rejected import rows and their reasons in Django admin."""

    list_display = ("source", "source_row", "issue_type", "created_at")
    list_filter = ("source", "issue_type")
    readonly_fields = ("source", "source_row", "issue_type", "detail", "raw_data", "created_at")
