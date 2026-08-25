## Task 4 — Data Issues Report

The three supplied CSV files contain several schema, formatting, quality,
and duplicate-resolution problems. The following table documents each issue
identified during the import process and the solution implemented in the
Django data pipeline.

| # | Data quality problem | Evidence / example | Solution implemented |
|---|---|---|---|
| 1 | Different column names for the same data | `Full Name`, `worker_name`, and `Name` all represent a person's name. Similar differences exist for email, phone, and city. | Each source is mapped explicitly into a common `Person` schema before processing. The CSV upload pipeline also recognizes supported aliases and converts them into one normalized structure. |
| 2 | Inconsistent text casing | Names, emails, cities, statuses, and skills appear in uppercase, lowercase, or mixed case. | Text values are trimmed and normalized. Names and emails are lowercased for matching, while city and status values are converted into consistent canonical forms. |
| 3 | Extra and inconsistent whitespace | Some values contain leading, trailing, or repeated spaces. | Whitespace is stripped and repeated spaces inside names and text fields are collapsed. |
| 4 | Equivalent city names | The data contains variants such as `Gurgaon` / `Gurugram` and `Bangalore` / `Bengaluru`. | Known city aliases are mapped to canonical values such as `gurugram` and `bengaluru`. |
| 5 | Different phone number formats | Phone numbers contain `+91`, leading `0`, spaces, and other punctuation. | Non-digit characters are removed. Indian country prefixes and trunk zeros are handled so that equivalent phone numbers can be compared consistently. |
| 6 | Duplicate people across source systems | The same person may appear in multiple CSV files with matching normalized email or phone values. | Records are grouped using normalized email and phone identifiers and merged into a single consolidated `Person` record. |
| 7 | Missing identifiers in some sources | One source may contain an email but no phone, while another may contain a phone but no email. | Matching uses whichever strong identifier is available. A record must contain a valid name and at least one usable identifier to be accepted. |
| 8 | Ambiguous people with the same name | A name by itself does not guarantee that two records represent the same person. | Name alone is never used as a merge key. `name + city` is only used as a conservative fallback when the match is one-to-one and unambiguous. |
| 9 | Conflicting values after merging records | A matched person can have different city values, name variants, or different non-key information across sources. | Source priority is applied for conflicting non-empty values. Conflicts are reported during import, while compatible information such as skills is combined instead of discarded. |
| 10 | Inconsistent date formats | Dates appear in formats such as `24-07-2026`, `2026-08-03`, `19 Jul 2026`, and `08/19/2026`. | Supported date formats are parsed into a standard database date value. Invalid or unparseable dates are left empty rather than being converted incorrectly. |
| 11 | Inconsistent compensation formats | Some records use annual CTC values, while gig-worker records contain formats such as `1415/hr` or `73k/month`. | Comparable CTC values are normalized where possible. Gig-worker rate information is stored separately as an amount and unit so that hourly and monthly values are not incorrectly merged with annual CTC. |
| 12 | Skills contain inconsistent casing and duplicates | Skills may appear with different capitalization or repeated multiple times. | Skills are lowercased, whitespace-normalized, deduplicated within each record, and combined when multiple source records are merged. |
| 13 | Status and verification values are inconsistent | Examples include `Active`, `ACTIVE`, `paused`, `Y`, `yes`, and `No`. | Status values are normalized to canonical lowercase values. Verification values are standardized to `Yes` or `No`. |
| 14 | Malformed source rows | Some rows contain missing identity data, shifted columns, invalid email values, or repeated header rows inside the data. | Invalid rows are rejected instead of being imported. Each rejected row is recorded as an `ImportIssue` so that the problem can be inspected later. |
| 15 | CSV upload structure can vary | Uploaded CSV files may use different supported headers or contain blank rows and invalid structures. | The CSV normalization layer validates headers, maps supported aliases to canonical field names, skips blank rows, and rejects malformed structures before data reaches the n8n workflow. |
| 16 | Duplicate identifiers during automation | A newly uploaded CSV may contain people already present in the consolidated database. | The normalized CSV is forwarded to an n8n workflow, which sends each record to the Django duplicate-check API. The API checks normalized email and phone values against the existing database and returns whether the record is a duplicate and the match type. |

# Stuck Log

## 1. SQL Server Connection with Django

**Problem:**  
The project was required to use the existing SQL Server database, but Django initially could not connect properly to the `SQLEXPRESS` instance.

**What I tried:**  
I checked whether the `MSSQL$SQLEXPRESS` service was running and verified the database name, SQL Server instance name, ODBC driver, and Django database configuration.

**Resolution:**  
The connection settings were corrected to use the existing SQL Server Express instance with `mssql-django` and `ODBC Driver 18 for SQL Server`. The connection parameters were also configured for the local development environment.

**Rejected approach:**  
I did not switch to SQLite because the project was already set up to work with SQL Server, and I wanted to keep the database implementation consistent with the project requirements.

---
## 2. Understanding CSV Mapping and Building the Duplicate Check Workflow

**Problem:**  
Initially, I was not clear about how the duplicate-check workflow should map data coming from different CSV files. The three source files used different column names and structures, so I was unsure how fields such as name, email, phone, and city should be mapped into one common format for duplicate checking.

**What I tried:**  
I first examined the structure and columns of all three CSV files to understand how the same information was represented differently across the sources. I compared fields such as `Full Name`, `worker_name`, `Name`, `Email`, `email_id`, `Phone`, `Phone Number`, `City`, and `location`.

I also used AI assistance to better understand the mapping and workflow design, especially how the normalized CSV data should move from Django to the n8n webhook and then to the duplicate-check API.

**Resolution:**  
After understanding the structure of all three CSV files, I created a common normalized mapping for the duplicate-check workflow:

```text
name
email
phone
city
## 2. CSV Data Was Correct in Django but Duplicate Detection Failed Through n8n

**Problem:**  
The duplicate-check API correctly detected an existing person when tested directly, but initially returned incorrect results when the same CSV data passed through the n8n workflow.

**What I tried:**  
I tested the Django duplicate API separately and inspected the output from the n8n CSV extraction node. I found that the uploaded CSV headers such as `Full Name`, `Email`, and `Phone` were not matching the field names being referenced later in the workflow.

**Resolution:**  
I added CSV header normalization so that different source headers are mapped to a common structure. The normalized fields are sent as `name`, `email`, `phone`, and `city`, allowing the Django duplicate API to receive consistent data.

**Rejected approach:**  
I did not create separate n8n workflows or branches for every possible CSV format. Instead, normalization happens before the duplicate check so the same workflow can handle supported header variations.

---

## 3. Testing the n8n Webhook with CSV File Upload

**Problem:**  
While testing the n8n webhook, the initial PowerShell command failed because the expected file upload parameter was not supported. Later, the n8n test webhook returned a `webhook is not registered` error.

**What I tried:**  
I first attempted to upload the CSV using `Invoke-RestMethod` with the `-Form` parameter. After that failed, I switched to `curl.exe` to send the CSV as multipart form data.

**Resolution:**  
The file upload worked successfully using `curl.exe` with multipart form data. I also learned that the n8n test webhook only works after clicking `Execute Workflow`, which temporarily registers the webhook for testing.

**Rejected approach:**  
I did not replace the CSV upload with manually entered JSON data because the required workflow needed to process an actual uploaded CSV file.