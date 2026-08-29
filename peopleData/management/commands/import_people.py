from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from peopleData.models import ImportIssue, Person, PersonSourceRecord
from peopleData.utils import (clean_city, clean_ctc, clean_date, clean_email,
    clean_name, clean_phone, clean_rate, clean_status, clean_text, clean_verified)


def non_empty(value):
    """Treat pandas NaN values and empty strings as missing source data."""
    return value not in (None, "") and not pd.isna(value)


def clean_experience(value):
    """Parse a source experience value without rejecting the complete row."""
    try:
        return float(clean_text(value)) if clean_text(value) else None
    except ValueError:
        return None


def clean_projects(value):
    """Parse a source project count without rejecting the complete row."""
    try:
        return int(float(clean_text(value))) if clean_text(value) else None
    except ValueError:
        return None


def normalize_skills(value):
    """Normalize, de-duplicate, and retain skills in their source order."""
    skills = []
    for item in clean_text(value).split(","):
        skill = " ".join(item.lower().split())
        if skill and skill not in skills:
            skills.append(skill)
    return ", ".join(skills) or None


class UnionFind:
    """Track record groups connected by shared strong identifiers."""
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first, second):
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


class Command(BaseCommand):
    help = "Normalize, deduplicate, and import the three people CSV exports into SQL Server."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report the merge without writing to SQL Server.")

    def handle(self, *args, **kwargs):
        """Load, normalize, merge, verify, and optionally persist source rows."""
        base_dir = Path(__file__).resolve().parents[3]
        data_dir = base_dir / "data"
        source1 = pd.read_csv(data_dir / "source1_naukri_applicants.csv", dtype=str, keep_default_na=False)
        source2 = pd.read_csv(data_dir / "source2_gig_workers.csv", dtype=str, keep_default_na=False)
        source3 = pd.read_csv(data_dir / "source3_cbnexus_contacts.csv", dtype=str, keep_default_na=False)

        records, rejected = [], []

        def add_record(source, row_number, **values):
            if not values["name"] or not (values["email"] or values["phone"]):
                rejected.append((source, row_number, "missing name or email/phone"))
                return
            values["source"] = source
            values["row_number"] = row_number
            records.append(values)

        for index, row in source1.iterrows():
            add_record("source1", index + 2, name=clean_name(row["Full Name"]),
                email=clean_email(row["Email"]), phone=clean_phone(row["Phone"]),
                city=clean_city(row["City"]), experience_years=clean_experience(row["Experience (Years)"]),
                current_ctc=clean_ctc(row["Current CTC"]), applied_date=clean_date(row["Applied Date"]),
                skills=normalize_skills(row["Skills"]), rate=None, status=None, verified=None,
                projects_completed=None)

        for index, row in source2.iterrows():
            email = clean_email(row["email_id"])
            if email and "@" not in email:
                rejected.append(("source2", index + 2, "invalid email column / shifted row"))
                continue
            add_record("source2", index + 2, name=clean_name(row["worker_name"]), email=email,
                phone=None, city=clean_city(row["location"]), experience_years=None,
                current_ctc=None, applied_date=None, skills=normalize_skills(row["skill_tags"]),
                rate=clean_rate(row["rate"]), status=clean_status(row["status"]), verified=None,
                projects_completed=None)

        for index, row in source3.iterrows():
            if clean_name(row["Name"]) == "name" and clean_phone(row["Phone Number"]) == "":
                rejected.append(("source3", index + 2, "repeated header row"))
                continue
            add_record("source3", index + 2, name=clean_name(row["Name"]), email=None,
                phone=clean_phone(row["Phone Number"]), city=clean_city(row["City"]),
                experience_years=None, current_ctc=None, applied_date=None, skills=None, rate=None,
                status=None, verified=clean_verified(row["Verified"]),
                projects_completed=clean_projects(row["Projects Completed"]))

        self.stdout.write(f"Loaded records: {len(records)}; rejected invalid rows: {len(rejected)}")
        for source, row_number, reason in rejected:
            self.stdout.write(f"  Rejected {source} row {row_number}: {reason}")

        groups = UnionFind(len(records))
        identifiers = {"email": defaultdict(list), "phone": defaultdict(list)}
        for index, record in enumerate(records):
            for field in identifiers:
                if record[field]:
                    identifiers[field][record[field]].append(index)

        strong_matches = 0
        for field in identifiers:
            for indexes in identifiers[field].values():
                for index in indexes[1:]:
                    groups.union(indexes[0], index)
                    strong_matches += 1

        # Name + city is only used for an exact two-record, one-to-one fallback.
        # This keeps ambiguous same-name people (for example, Arjun Mehta) separate.
        name_city_indexes = defaultdict(list)
        for index, record in enumerate(records):
            if record["name"] and record["city"]:
                name_city_indexes[(record["name"], record["city"])].append(index)

        fallback_matches = 0
        for indexes in name_city_indexes.values():
            if len(indexes) == 2 and len({groups.find(index) for index in indexes}) == 2:
                groups.union(indexes[0], indexes[1])
                fallback_matches += 1

        components = defaultdict(list)
        for index, record in enumerate(records):
            components[groups.find(index)].append(record)

        fields = ("name", "email", "phone", "city", "experience_years", "current_ctc",
                  "applied_date", "skills", "rate", "status", "verified", "projects_completed")
        merged_people, conflicts = [], []
        for component in components.values():
            person = {}
            for field in fields:
                values = [record[field] for record in component if non_empty(record[field])]
                person[field] = values[0] if values else None
                distinct = list(dict.fromkeys(values))
                if len(distinct) > 1 and field != "skills":
                    conflicts.append((person["name"], field, distinct))

            skills = []
            for record in component:
                for skill in (record["skills"] or "").split(", "):
                    if skill and skill not in skills:
                        skills.append(skill)
            person["skills"] = ", ".join(skills) or None
            person["sources"] = ", ".join(sorted({record["source"] for record in component}))
            person["source_rows"] = ", ".join(f"{r['source']}:{r['row_number']}" for r in component)
            merged_people.append(person)

        merged_people.sort(key=lambda person: (person["name"], person["email"] or "", person["phone"] or ""))

        def duplicate_values(field):
            values = [person[field] for person in merged_people if person[field]]
            return sorted(value for value, count in Counter(values).items() if count > 1)

        duplicate_emails = duplicate_values("email")
        duplicate_phones = duplicate_values("phone")
        self.stdout.write(self.style.SUCCESS("\nMerge verification complete."))
        self.stdout.write(f"Exact email/phone matches merged: {strong_matches}")
        self.stdout.write(f"Safe name+city fallback matches merged: {fallback_matches}")
        self.stdout.write(f"Final merged people: {len(merged_people)}")
        self.stdout.write(f"Duplicate emails remaining: {len(duplicate_emails)}")
        self.stdout.write(f"Duplicate phones remaining: {len(duplicate_phones)}")
        self.stdout.write(f"Field conflicts retained for review: {len(conflicts)}")

        if duplicate_emails or duplicate_phones:
            self.stdout.write(self.style.WARNING("Duplicate strong identifiers need review:"))
            for value in duplicate_emails:
                self.stdout.write(f"  email: {value}")
            for value in duplicate_phones:
                self.stdout.write(f"  phone: {value}")
        if conflicts:
            self.stdout.write(self.style.WARNING("\nConflicting fields (source1 takes priority):"))
            for name, field, values in conflicts:
                self.stdout.write(f"  {name} — {field}: {values}")

        if kwargs["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: no database writes were made."))
            return

        # A rerun replaces the consolidated snapshot atomically. Every source
        # row remains queryable through PersonSourceRecord for provenance.
        component_by_rows = {
            tuple(f"{record['source']}:{record['row_number']}" for record in component): component
            for component in components.values()
        }
        with transaction.atomic():
            PersonSourceRecord.objects.all().delete()
            ImportIssue.objects.all().delete()
            Person.objects.filter(audio_submissions__isnull=True).delete()
            for merged in merged_people:
                source_rows = tuple(merged["source_rows"].split(", "))
                source_summary = merged["sources"]
                person = None
                if merged["email"]:
                    person = Person.objects.filter(email__iexact=merged["email"]).order_by("id").first()
                if person is None and merged["phone"]:
                    person = Person.objects.filter(phone=merged["phone"]).order_by("id").first()
                if person is None and merged["name"]:
                    person = Person.objects.filter(name__iexact=merged["name"]).order_by("id").first()
                if person is None:
                    person = Person.objects.create(
                        **{field: merged[field] for field in fields}, source_summary=source_summary
                    )
                else:
                    for field in fields:
                        setattr(person, field, merged[field])
                    person.source_summary = source_summary
                    person.save(update_fields=fields + ("source_summary",))
                PersonSourceRecord.objects.bulk_create([
                    PersonSourceRecord(
                        person=person, source=record["source"], source_row=record["row_number"], raw_data={},
                        normalized_data={field: (record[field].isoformat() if hasattr(record[field], "isoformat") else record[field]) for field in fields},
                    ) for record in component_by_rows[source_rows]
                ])
            ImportIssue.objects.bulk_create([
                ImportIssue(source=source, source_row=row_number, issue_type="rejected_row", detail=reason, raw_data={})
                for source, row_number, reason in rejected
            ])
        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(merged_people)} people and {len(records)} source rows into SQL Server; "
            f"{len(rejected)} invalid rows quarantined."
        ))
