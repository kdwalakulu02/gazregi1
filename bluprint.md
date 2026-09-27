Yes. I would build this as a **file-first, static-search system now**, with a clean migration path later.

The key architecture decision is:

> **Files are the source of truth → Pagefind is the search engine → database comes later only when the product actually needs one.**

At 2,000–10,000 notices, a prebuilt static index is likely to be extremely fast and essentially free to operate. A database does not automatically make public search faster.

Below is the blueprint I'd paste into the repo as `BLUEPRINT.md` and use as the instruction set for VS Code + AI.

# GazetteRegistry.com — MVP Engineering Blueprint

## 0. Product

GazetteRegistry is an independent search and discovery layer over official government Gazette publications.

### Core proposition

> Search government Gazette records by name, company, organization, tender, topic, location, Gazette number or date — without needing to know which Gazette contained the information.

### MVP principles

1. Do not host the original Gazette PDFs.
2. Store the official source URL for every record.
3. Extract structured information from official publications.
4. Generate our own summaries and classifications.
5. Preserve exact source/page provenance.
6. Make search extremely fast.
7. Keep storage extremely small.
8. Use GitHub as the source repository and CI/CD system.
9. Use Cloudflare for public deployment.
10. Keep the storage layer replaceable so PostgreSQL can be introduced later without redesigning the frontend.

---

# 1. Technology Stack

## MVP

### Data ingestion

* Python 3.12+
* PyMuPDF (`fitz`) for PDF text extraction
* Pydantic for schema validation
* `orjson` for fast JSON processing
* `rapidfuzz` for name/entity normalization
* Python `re` for deterministic field extraction
* Optional LLM/AI enrichment after deterministic extraction

### Storage

* JSONL / NDJSON
* Small JSON dictionaries
* GZIP-compressed extracted source text where appropriate

### Frontend

* Static HTML
* CSS
* Minimal vanilla JavaScript
* Pagefind for full-text search
* No runtime database required

### Deployment

```text
GitHub Repository
       ↓
GitHub Actions
       ↓
Build static site
       ↓
Pagefind index
       ↓
Cloudflare Pages
```

---

# 2. Repository Structure

```text
gazetteregistry/
│
├── data/
│   └── lk/
│       ├── 2025/
│       │   └── 2025-01-03-2365/
│       │       ├── issue.json
│       │       ├── notices.ndjson
│       │       └── text.jsonl.gz
│       │
│       └── 2026/
│           └── 2026-01-02-2417/
│               ├── issue.json
│               ├── notices.ndjson
│               └── text.jsonl.gz
│
├── dictionaries/
│   ├── categories.json
│   ├── subcategories.json
│   ├── ministries.json
│   ├── departments.json
│   ├── locations.json
│   ├── synonyms.json
│   └── stopwords.json
│
├── entities/
│   └── lk/
│       ├── people.ndjson
│       ├── companies.ndjson
│       ├── organisations.ndjson
│       ├── locations.ndjson
│       └── refs.ndjson
│
├── schemas/
│   ├── issue.schema.json
│   ├── notice.schema.json
│   └── entity.schema.json
│
├── scripts/
│   ├── discover.py
│   ├── download.py
│   ├── extract_pdf.py
│   ├── split_notices.py
│   ├── classify.py
│   ├── extract_fields.py
│   ├── extract_entities.py
│   ├── normalize_entities.py
│   ├── validate.py
│   ├── build_site.py
│   └── build_all.py
│
├── src/
│   ├── templates/
│   │   ├── home.html
│   │   ├── search.html
│   │   ├── notice.html
│   │   └── entity.html
│   │
│   ├── css/
│   │   └── main.css
│   │
│   └── js/
│       └── app.js
│
├── public/
│   ├── favicon.svg
│   └── robots.txt
│
├── dist/
│   └── generated during build
│
├── requirements.txt
├── package.json
├── BLUEPRINT.md
└── .github/
    └── workflows/
        └── deploy.yml
```

---

# 3. Why NDJSON Instead of Large JSON Arrays

Do NOT use:

```text
notices.json
[
  {...},
  {...},
  {...}
]
```

Use:

```text
notices.ndjson
{"uid":"LK-2026-2480-PROC-001",...}
{"uid":"LK-2026-2480-PROC-002",...}
{"uid":"LK-2026-2480-APPT-001",...}
```

Advantages:

* append-friendly
* easy Git diffs
* stream processing
* low memory consumption
* fast Python processing
* individual records can be processed without loading an entire array
* easy migration into SQLite/PostgreSQL later

---

# 4. Issue Schema

Each Gazette issue gets one compact metadata file.

Example:

```json
{
  "issue_id": "LK-2026-2480",
  "country": "LK",
  "gazette_no": "2480",
  "gazette_type": "regular",
  "publication_date": "2026-03-13",
  "language": ["en", "si", "ta"],
  "parts": ["I", "IIA", "IIB", "III"],
  "source_url": "https://documents.gov.lk/...",
  "discovered_at": "2026-09-27",
  "parser_version": "0.1.0"
}
```

The issue metadata should not be duplicated into every notice.

---

# 5. Notice Schema

Each notice should be one NDJSON record.

Example:

```json
{
  "uid": "LK-2026-2480-PROC-001",
  "issue_id": "LK-2026-2480",

  "page_start": 12,
  "page_end": 14,

  "section": "IIB",

  "category": "PROC",
  "subcategory": "CIVIL_WORKS",

  "issuer_id": "RDA",

  "title": "Construction of Road Drainage Works",

  "summary": "Notice inviting bids for road drainage construction works.",

  "keywords": [
    "road",
    "drainage",
    "construction",
    "bid"
  ],

  "locations": [
    "Colombo"
  ],

  "tender": {
    "reference": "RDA/PROC/2026/014",
    "bid_security_lkr": 500000,
    "document_deadline": null,
    "closing_date": "2026-04-15",
    "closing_time": "14:00"
  },

  "entities": [
    "org:rda"
  ],

  "source": {
    "url": "https://documents.gov.lk/...",
    "page_start": 12,
    "page_end": 14
  }
}
```

---

# 6. Do Not Duplicate Long Strings

For small data, readability is more important than microscopic optimization.

However, avoid repeating huge values.

Bad:

```json
{
  "ministry": "Ministry of Transport and Highways",
  ...
}
```

2,000 times.

Better:

```json
{
  "issuer_id": "MOT"
}
```

Dictionary:

```json
{
  "MOT": "Ministry of Transport and Highways"
}
```

Use IDs for:

* ministries
* departments
* locations
* categories
* subcategories
* entities

The build process resolves them for display.

---

# 7. Classification System

Use a two-level taxonomy.

```text
PROC
  CIVIL_WORKS
  GOODS_SUPPLIES
  CONSULTANCY
  MAINTENANCE
  IT
  AUCTION

APPT
  EXECUTIVE
  PUBLIC_SERVICE
  BOARDS
  POLICE
  MILITARY

RECR
  VACANCIES
  COMPETITIVE_EXAMS
  DEPARTMENTAL_EXAMS
  RESULTS

LEGL
  LAND
  INSOLVENCY
  ESTATE
  COURT
  LEGAL_NOTICE

REGL
  ACTS
  REGULATIONS
  MINISTERIAL_ORDERS
  EXTRAORDINARY_NOTIFICATION

PROP
  TRADEMARK
  PATENT
  DESIGN
```

Classification must describe the notice itself.

Do NOT make the Gazette section the classification.

For example:

```text
Part IIB
    ↓
inspect content
    ↓
Tender
    ↓
PROC/CIVIL_WORKS
```

Another section could also contain a tender:

```text
Part IV
    ↓
inspect content
    ↓
Tender
    ↓
PROC/CIVIL_WORKS
```

---

# 8. Extraction Philosophy

The extractor must be deterministic wherever factual precision matters.

Never let an LLM invent:

* dates
* amounts
* tender numbers
* Gazette numbers
* ministry names
* reference numbers
* deadlines
* page numbers

Those values must come directly from extracted source text.

## Deterministic fields

Use:

* regex
* string matching
* section markers
* known heading patterns
* date parsing
* numeric parsing
* dictionary matching

## AI fields

AI can optionally generate:

* short summary
* keywords
* category suggestion
* subcategory suggestion
* entity normalization
* semantic tags

AI output must be treated as enrichment, not authoritative source data.

---

# 9. PDF Extraction Pipeline

Initial pipeline:

```text
Official Gazette URL
        ↓
download PDF
        ↓
PyMuPDF
        ↓
extract page text
        ↓
normalize whitespace
        ↓
detect section boundaries
        ↓
detect individual notices
        ↓
extract fields
        ↓
classify
        ↓
extract entities
        ↓
validate
        ↓
write NDJSON
```

Do not OCR everything.

First attempt normal PDF text extraction.

Only flag a document/page for OCR if the PDF contains no usable text layer.

Multilingual OCR should be treated as a later enhancement.

---

# 10. Raw Text Storage

Keep two concepts separate.

## Structured record

```text
notices.ndjson
```

Contains only normalized useful fields.

## Search/source text

```text
text.jsonl.gz
```

Contains extracted text needed for search/build.

Example:

```json
{"uid":"LK-2026-2480-PROC-001","text":"..."}
{"uid":"LK-2026-2480-PROC-002","text":"..."}
```

GZIP it.

That keeps the repository much smaller than thousands of individual `.txt` files.

For MVP, the search index may expose some of that text in the generated static build because Pagefind must index it. This is an intentional MVP trade-off.

Later, the raw/search text can move to private object storage or a database.

---

# 11. Entity Architecture

The most valuable long-term feature is entity search.

Types:

```text
person
company
organisation
location
tender
law
regulation
property_reference
```

Example:

```json
{
  "entity_id": "person:lk:john-perera",
  "type": "person",
  "canonical_name": "John Perera",
  "aliases": [
    "Perera John",
    "J. Perera"
  ]
}
```

Entity references:

```json
{
  "entity_id": "person:lk:john-perera",
  "notice_uid": "LK-2026-2480-APPT-014",
  "page": 31,
  "confidence": 0.98
}
```

The entity should point back to source records.

Do NOT initially construct speculative relationships between people.

Do not infer:

* family
* wealth
* political preference
* personal relationships
* credit risk
* addresses not explicitly stated
* estimated assets

The MVP is:

> person/entity → official Gazette records.

---

# 12. Search Architecture

The frontend should never load the entire database into the browser.

Bad:

```text
download all JSON
↓
JavaScript filters 2,500 records
```

Better:

```text
Static HTML pages
       ↓
Pagefind indexing
       ↓
small search index shards
       ↓
browser searches only required index data
```

Each notice gets a static page:

```text
/notices/LK-2026-2480-PROC-001/
```

The page contains:

* title
* category
* date
* issuer
* summary
* keywords
* extracted tender fields
* source page
* official source button

Pagefind indexes the searchable content.

---

# 13. Pagefind Content Strategy

Index:

```text
title
summary
keywords
issuer
department
location
Gazette number
tender reference
dates
searchable source text
```

Do not make the user wait for a server-side query.

Search should feel instantaneous.

Example:

```text
road drainage
```

Results:

```text
12 results

Gazette 2480/18
Road drainage construction...

Gazette 2478/42
Drain rehabilitation...

Gazette 2473/11
Road improvement...
```

---

# 14. Search Filters

MVP filters:

```text
Country
Category
Subcategory
Ministry
Department
Gazette type
Year
Date
District
```

Later:

```text
Closing date
Tender value
Language
Entity type
Person
Company
```

---

# 15. Entity Search UX

A search for:

```text
John Perera
```

should produce:

```text
John Perera

4 Gazette records found

Appointments
2

Legal notices
1

Land
1
```

Then:

```text
2026-03-13
Gazette 2480/...
Appointment notice
View official source →

2025-09-19
Gazette 2460/...
Land notice
View official source →
```

Do not initially create a giant "personal dossier".

The page is a navigation layer into the official records.

---

# 16. Source Provenance

Every record must tell us where it came from.

Required:

```json
{
  "source": {
    "url": "...",
    "gazette_no": "2480",
    "page_start": 31,
    "page_end": 32,
    "language": "en"
  }
}
```

Also store:

```json
{
  "parser_version": "0.1.0",
  "extraction_method": "pymupdf",
  "extracted_at": "2026-09-27T..."
}
```

This allows correction and reproducibility.

---

# 17. Record UID

UID format:

```text
LK-YYYY-GAZETTE-CATEGORY-SEQUENCE
```

Examples:

```text
LK-2026-2480-PROC-001
LK-2026-2480-PROC-002
LK-2026-2480-APPT-001
LK-2026-2480-RECR-001
```

UID must never depend on title text.

If title changes, UID must remain stable.

---

# 18. Ingestion Scripts

## discover.py

Find available Gazette publications.

Responsibilities:

* discover issue URLs
* identify regular Gazettes
* identify extraordinary Gazettes
* detect missing issues
* save discovered URLs

Do not assume exactly 104 issues per year.

Use the actual archive.

---

## download.py

Input:

```text
issue_id
source_url
```

Output:

```text
temporary PDF
```

Never make download code dependent on a specific filename pattern if the source site changes.

---

## extract_pdf.py

Input:

```text
PDF
```

Output:

```text
page text
```

Store page boundaries.

---

## split_notices.py

Detect:

* section headings
* notice boundaries
* title patterns
* page ranges

Output:

```text
notice candidates
```

---

## extract_fields.py

Extract:

```text
Gazette number
Date
Issuer
Department
Tender reference
Deadline
Amounts
Location
```

All deterministic where possible.

---

## classify.py

Assign:

```text
category
subcategory
```

Using rules and dictionaries.

---

## extract_entities.py

Extract:

```text
people
companies
organisations
locations
tender references
```

---

## normalize_entities.py

Normalize:

```text
John Perera
J. Perera
PERERA, JOHN
Perera John
```

into a canonical entity where evidence supports that they are the same.

Do not aggressively merge uncertain people.

---

## validate.py

Validation rules:

```text
UID exists
Gazette number exists
Date valid
Source URL valid
Category valid
Page number valid
No duplicate UID
Tender date is valid
Tender closing date is not malformed
```

Validation failure must stop the build.

---

# 19. Build Pipeline

Command:

```bash
python scripts/build_all.py
```

Pipeline:

```text
1. Validate data
2. Load dictionaries
3. Load notices
4. Load entities
5. Generate static HTML
6. Generate entity pages
7. Generate search content
8. Run Pagefind
9. Run link checks
10. Write dist/
```

Build failure means:

```text
NO DEPLOYMENT
```

---

# 20. GitHub Actions

Initial workflow:

```text
push to main
      ↓
GitHub Actions
      ↓
Install Python
      ↓
Install Node
      ↓
Validate data
      ↓
Build site
      ↓
Run Pagefind
      ↓
Deploy
```

Later:

```text
scheduled workflow
       ↓
discover new Gazettes
       ↓
download
       ↓
extract
       ↓
validate
       ↓
commit new data
       ↓
build
       ↓
deploy
```

For the first MVP, ingestion can remain manual in GitHub Codespaces.

---

# 21. Codespaces Workflow

In Codespaces:

```bash
git clone ...
cd gazetteregistry

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python scripts/discover.py --country lk --year 2026

python scripts/download.py --year 2026

python scripts/extract_pdf.py --year 2026

python scripts/split_notices.py --year 2026

python scripts/extract_fields.py --year 2026

python scripts/classify.py --year 2026

python scripts/extract_entities.py --year 2026

python scripts/normalize_entities.py --year 2026

python scripts/validate.py

python scripts/build_all.py
```

Then:

```bash
git add .
git commit -m "Add Gazette data"
git push
```

GitHub handles deployment.

---

# 22. MVP Build Order

Do NOT begin with two complete years.

Build in this order.

## Phase 1 — One Gazette

Process exactly one issue.

Prove:

```text
PDF
→ extraction
→ notices
→ classification
→ page generation
→ search
```

---

## Phase 2 — Ten Gazettes

Test:

```text
duplicate detection
different sections
different issuers
different notice formats
search
```

---

## Phase 3 — One Month

Run approximately one month's publications.

Test:

```text
name search
company search
tender search
date filtering
issuer filtering
```

---

## Phase 4 — Three Months

Now test:

```text
entity normalization
Pagefind performance
repository size
build time
```

---

## Phase 5 — Full 2026

Only after the previous stages work:

```text
2026 archive
+
extraordinary Gazettes
```

Then optionally:

```text
2025 archive
```

---

# 23. Storage Strategy

## MVP

Use:

```text
JSONL
+
GZIP source text
+
static HTML
+
Pagefind
```

No production database.

This is intentionally simple.

---

# 24. Should We Eventually Move to a Database?

Yes — but **not because search is slow**.

Move to a database when you need:

```text
user accounts
subscriptions
saved searches
email alerts
live ingestion
admin editing
duplicate resolution
complex relationships
analytics
API access
multi-country scaling
```

## Recommended future database

PostgreSQL.

Not MongoDB.

Not Elasticsearch initially.

Recommended future architecture:

```text
                 PostgreSQL
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
       notices    entities    users
          │          │          │
          └──────────┼──────────┘
                     ↓
             Search generation
                     ↓
                 Pagefind
                     ↓
              Public website
```

This is important:

## Even after PostgreSQL, keep Pagefind.

PostgreSQL becomes the authoritative database.

Pagefind remains the extremely fast public search layer.

That gives:

```text
database
   +
prebuilt static search index
```

rather than replacing Pagefind completely.

---

# 25. When PostgreSQL Arrives

Eventually:

```text
PDF
 ↓
Python ingestion
 ↓
PostgreSQL
 ↓
search/index builder
 ↓
Pagefind
 ↓
Cloudflare
```

The frontend does not need to know whether the source data came from:

```text
JSON files
```

or:

```text
PostgreSQL
```

That is why the schemas must be defined now.

---

# 26. When a Dedicated Search Engine Becomes Necessary

Do NOT add:

* Elasticsearch
* OpenSearch
* Typesense
* Meilisearch

during the MVP.

Consider them only when the corpus becomes large enough that static indexing no longer meets the requirements.

Possible later options:

```text
PostgreSQL FTS
PostgreSQL + pg_trgm
Meilisearch
Typesense
OpenSearch
```

For GazetteRegistry, PostgreSQL full-text search plus trigram matching is likely the first thing to test before adding another service.

---

# 27. Extreme-Speed Rules

## Rule 1

Never query the server for every keystroke.

Use Pagefind.

## Rule 2

Never download the entire database to the browser.

Use search-index shards.

## Rule 3

Never store duplicated metadata.

Use IDs/dictionaries.

## Rule 4

Never parse PDFs at request time.

Everything is preprocessed.

## Rule 5

Never call an AI model during user search.

AI happens during ingestion.

## Rule 6

Never use AI to retrieve a factual value that can be extracted directly.

## Rule 7

Pre-generate pages.

Do not dynamically render 2,500 records on every visit.

---

# 28. Search Ranking

Initial ranking:

```text
Exact Gazette number
        >
Exact tender reference
        >
Exact entity name
        >
Title
        >
Issuer
        >
Keywords
        >
Full text
```

For example:

Search:

```text
RDA/PROC/2026/014
```

should put the exact tender notice first.

Search:

```text
road drainage
```

should rank notices containing both terms highly.

Search:

```text
John Perera
```

should prioritize exact entity matches over incidental text matches.

---

# 29. Normalization

Normalize search strings:

```text
lowercase
trim whitespace
normalize punctuation
normalize Unicode
collapse duplicate spaces
```

Example:

```text
"  John   PERERA "
```

becomes:

```text
"john perera"
```

But preserve the original display text separately.

---

# 30. Synonyms

Maintain:

```text
dictionaries/synonyms.json
```

Example:

```json
{
  "road": [
    "highway",
    "roadway",
    "rd"
  ],
  "construction": [
    "construction works",
    "civil works",
    "rehabilitation"
  ]
}
```

Do not blindly expand every query.

Use synonyms primarily for ranking/recall.

---

# 31. Search Fields

Each notice should effectively have:

```text
TITLE
SUMMARY
ISSUER
DEPARTMENT
LOCATION
CATEGORY
SUBCATEGORY
GAZETTE NUMBER
TENDER NUMBER
KEYWORDS
SOURCE TEXT
ENTITIES
```

Pagefind should index all appropriate fields.

---

# 32. Public Notice Page

Example:

```text
--------------------------------------------------

Gazette 2480/18

Construction of Road Drainage Works

13 March 2026

Category
Tenders & Procurement
Civil Works

Issuer
Road Development Authority

Location
Colombo

Tender Reference
RDA/PROC/2026/014

Closing
15 April 2026 — 14:00

Summary
Notice inviting bids for road drainage works...

[ View Official Gazette ]

Source
Department of Government Printing
Page 12–14

--------------------------------------------------
```

Do not reproduce the entire PDF as the main page.

---

# 33. Entity Page

Example:

```text
--------------------------------------------------

John Perera

Gazette records found: 4

Appointments
2

Legal notices
1

Other
1

2026-03-13
Appointment notice
Gazette 2480/...

2025-09-19
Legal notice
Gazette 2460/...

[ View official source ]

--------------------------------------------------
```

Avoid speculative profiles.

The entity page should be a structured index of official records.

---

# 34. Privacy / Data Handling

MVP rule:

> Only publish information that can be directly tied to the official source record.

Do not generate:

```text
wealth estimates
family relationships
political profiles
risk scores
credit scores
speculative identities
inferred addresses
inferred relationships
```

Every record must have a source.

Provide:

```text
Report an error
Request correction
```

---

# 35. Legal/Product Boundary

GazetteRegistry is:

```text
an independent search/index/monitoring service
```

It is not:

```text
the official Government Gazette
```

Footer:

> GazetteRegistry is an independent search and information service and is not affiliated with or operated by the Government of Sri Lanka. Official documents are linked to their original government source.

---

# 36. Monitoring / Revenue Layer

Do not charge initially for basic search.

Free:

```text
Search
Browse
View metadata
Open official source
```

Potential paid feature:

```text
Save a search
```

Example:

```text
"road construction"
```

Then:

```text
Notify me when a new matching Gazette appears.
```

Possible target:

```text
AUD 10/year
```

Only 10 paying users:

```text
10 × AUD 10
=
AUD 100/year
```

Later:

```text
Individual
Professional
Company
API
```

---

# 37. Future Alert Architecture

Later:

```text
New Gazette
     ↓
ingestion
     ↓
entity extraction
     ↓
classification
     ↓
search
     ↓
saved-search matcher
     ↓
alert queue
     ↓
email
```

At that point PostgreSQL becomes useful because users and subscriptions are dynamic.

---

# 38. Important Data Design Rule

Never let the frontend depend directly on the raw repository structure.

Frontend consumes a stable logical record:

```text
Notice
Issue
Entity
Source
```

Whether those eventually come from:

```text
JSON
```

or:

```text
PostgreSQL
```

must not matter to the frontend.

This is the migration strategy.

---

# 39. Definition of Done for MVP

The MVP is ready when:

```text
[ ] One Gazette downloads automatically
[ ] PDF text extracts correctly
[ ] Notices are detected
[ ] Notices receive stable UIDs
[ ] Categories are assigned
[ ] Issuers are normalized
[ ] Entity names are extracted
[ ] Source pages are recorded
[ ] Official URLs are recorded
[ ] JSONL validates
[ ] Static pages generate
[ ] Pagefind searches
[ ] Filters work
[ ] Exact name search works
[ ] Tender number search works
[ ] Gazette number search works
[ ] Official source links work
[ ] GitHub Actions builds successfully
[ ] Cloudflare deployment succeeds
[ ] Repository remains small
```

---

# 40. Final Architecture

## NOW

```text
Official Gazette
       ↓
Python in Codespace
       ↓
JSONL + compressed text
       ↓
GitHub
       ↓
GitHub Actions
       ↓
Static HTML
       ↓
Pagefind
       ↓
Cloudflare Pages
       ↓
Users
```

## LATER

```text
Official Gazette
       ↓
Python ingestion
       ↓
PostgreSQL
       ↓
Entity + search processing
       ↓
Pagefind/static search
       ↓
Cloudflare
       ↓
Users

             +
        user accounts
             +
        saved searches
             +
           alerts
             +
            API
```

## Most important architectural decision

**Do not move to a database just because the project grows.**

Move to PostgreSQL when the *business requirements* become dynamic.

For a read-only archive of several thousand or even many tens of thousands of notices:

> **static files + prebuilt search index = cheap, fast, simple, reliable.**

PostgreSQL should eventually become the **source-of-truth database**, while Pagefind remains the **high-speed public search layer**.

That gives GazetteRegistry the best combination:

**very low hosting cost + very fast search + easy Git versioning + clean future migration.**

I would start with **one Gazette issue and make the entire pipeline work end-to-end before touching the two-year archive**. The architecture above is deliberately set up so the same code can then process the whole archive without changing the frontend.
