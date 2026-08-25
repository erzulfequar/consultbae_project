import csv
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .views import normalize_csv_for_n8n


class NormalizeCsvForN8nTests(SimpleTestCase):
    def test_source_specific_headers_and_values_become_consistent(self):
        upload = SimpleUploadedFile(
            "workers.csv",
            b"email_id,worker_name,Phone Number,location,skill_tags\n"
            b" TEST@EXAMPLE.COM ,  Jane   Doe ,+91-90000 00001,Gurgaon , Python \n\n",
            content_type="text/csv",
        )

        result = normalize_csv_for_n8n(upload).decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(result)))

        self.assertEqual(rows, [{
            "email": "test@example.com",
            "name": "jane doe",
            "phone": "9000000001",
            "city": "gurugram",
            "skill_tags": "Python",
        }])

    def test_header_alias_collision_is_rejected(self):
        upload = SimpleUploadedFile("people.csv", b"Email,email\na@x.com,b@x.com\n")

        with self.assertRaisesMessage(ValueError, "normalize to duplicates"):
            normalize_csv_for_n8n(upload)
