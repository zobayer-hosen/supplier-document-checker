# AI-Powered Supplier Document Checker

## End-to-End Product Requirements Document (PRD)

**Version:** 1.1\
**Purpose:** BIAI AI Engineer -- Round 2, Task 1\
**Architecture:** Next.js + FastAPI + LangGraph + OpenAI + Neon
PostgreSQL\
**Deployment constraints:** No Docker, no CI/CD\
**Code standard:** Beginner-friendly, reusable, modular, and testable\
**Target delivery:** 72 hours

------------------------------------------------------------------------

# 1. Product Overview

## 1.1 Product summary

The Supplier Document Checker is a web application that evaluates
supplier quotations and their terms and conditions against a company
Purchase Request (PR) and company rules.

The application processes each supplier PDF independently. It extracts
information, verifies supporting evidence, compares the quotation with
the Purchase Request, applies deterministic business rules, and produces
one of three decisions:

-   **APPROVE** --- all required checks pass.
-   **REJECT** --- at least one rejection rule is triggered.
-   **NEEDS A PERSON TO CHECK** --- no rejection rule is established,
    but information is missing, unclear, conflicting, or triggers a
    review rule.

The system must never invent missing information. Every important
extracted value and every decision finding must be traceable to exact
document text and a page number whenever the source provides one.

## 1.2 Problem

Manual supplier-document checking takes time and can produce
inconsistent results. The application will help a reviewer identify
pricing, quantity, payment, delivery, tax, supplier-identification, and
contract-penalty issues in a consistent way.

## 1.3 Goals

1.  Process the supplied 10 supplier PDF files independently.
2.  Read the Purchase Request CSV and Company Rules Markdown file.
3.  Extract structured supplier and contract information.
4.  Validate extracted data and supporting evidence.
5.  Apply company rules using ordinary Python functions.
6.  Explain every decision with rule identifiers and document evidence.
7.  Save batches, documents, results, and human-review notes in Neon
    PostgreSQL.
8.  Measure actual extraction, evidence, and decision accuracy against
    manually checked ground truth.

## 1.4 Out of scope

-   Docker and Docker Compose.
-   CI/CD pipelines.
-   Kubernetes and microservices.
-   Redis, Celery, and message brokers.
-   Autonomous agents that make their own business decisions.
-   Automatic supplier emails, contract signing, or purchase-order
    creation.
-   Complex authentication and multi-role access control for Version 1.

------------------------------------------------------------------------

# 2. Technology Stack

  -----------------------------------------------------------------------
  Area                    Technology              Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                Next.js + TypeScript    Upload pages,
                                                  dashboard, results,
                                                  evidence display

  Styling                 Tailwind CSS            Responsive user
                                                  interface

  Backend                 Python + FastAPI        APIs and application
                                                  logic

  Workflow                LangGraph               Fixed, traceable
                                                  processing steps

  LLM                     OpenAI API              Extract structured
                                                  information only

  PDF text                PyMuPDF                 Extract text page by
                                                  page

  OCR fallback            Tesseract               Read supported scanned
                                                  PDFs

  Schema validation       Pydantic                Validate extracted data
                                                  types and structure

  Database                Neon PostgreSQL         Persist batches,
                                                  documents, findings,
                                                  decisions

  ORM                     SQLAlchemy              Python database access

  Migrations              Alembic                 Create and update
                                                  database tables

  Tests                   Pytest                  Unit and integration
                                                  tests

  API documentation       FastAPI Swagger         Interactive API
                                                  documentation

  Version control         Git + GitHub            Source code history
  -----------------------------------------------------------------------

**Important architecture rule:** The LLM extracts information. Python
checks the rules and makes the automated decision. LangGraph controls
the order of operations. The database stores the result and evidence.

------------------------------------------------------------------------

# 3. Users and Main Use Cases

## 3.1 Primary user

A company employee or evaluator who uploads supplier documents and
reviews the system's findings.

## 3.2 Main use cases

1.  Create an evaluation batch.
2.  Upload supplier PDFs, the Purchase Request CSV, and Company Rules
    Markdown file.
3.  Start evaluation.
4.  See processing progress.
5.  View each supplier's decision.
6.  Open a supplier result and inspect extracted values, rule checks,
    and evidence.
7.  Record a human-review note for documents requiring review.
8.  Review the evaluation metrics for all 10 documents.

------------------------------------------------------------------------

# 4. Input Files and Validation

The expected sample files are:

``` text
sample-data/
├── supplier-pack-01.pdf
├── supplier-pack-02.pdf
├── supplier-pack-03.pdf
├── supplier-pack-04.pdf
├── supplier-pack-05.pdf
├── supplier-pack-06.pdf
├── supplier-pack-07.pdf
├── supplier-pack-08.pdf
├── supplier-pack-09.pdf
├── supplier-pack-10.pdf
├── purchase-request.csv
└── company-rules.md
```

## 4.1 Upload requirements

-   Accept multiple PDF files, one CSV file, and one Markdown file.
-   Validate file extension, MIME type, file size, and PDF readability
    on the backend.
-   Do not trust the filename or browser-provided MIME type alone.
-   Prevent duplicate files in the same batch.
-   Show clear errors for missing or invalid input.
-   Require the necessary inputs before evaluation starts.
-   Keep each supplier's extracted information separate.

## 4.2 Purchase Request CSV

The parser must identify the actual column names in the supplied CSV.
The logical fields needed are:

-   Item name or item identifier.
-   Requested quantity.
-   Maximum unit price.
-   Currency, if available.

Do not assume column names before inspecting the supplied CSV. Map its
real column names to the internal schema. Reject an invalid CSV with a
useful message instead of silently guessing.

## 4.3 Company rules Markdown

Read the provided `company-rules.md`. Implement the supplied rules in a
centralized Python rule engine. The LLM must not rewrite, override, or
decide company policy.

------------------------------------------------------------------------

# 5. Business Rules

## 5.1 Rejection rules

A supplier document is rejected if any one of these conditions is
established:

  -----------------------------------------------------------------------
  Code                    Rule                    Rejection condition
  ----------------------- ----------------------- -----------------------
  R01                     Unit price              Quoted unit price is
                                                  more than 3% above the
                                                  Purchase Request
                                                  maximum

  R02                     Advance payment         Advance payment is
                                                  greater than 20%

  R03                     Late-delivery penalty   Penalty clause is
                                                  missing or penalty is
                                                  below 0.5% of order
                                                  value per week

  R04                     TIN/BIN                 Required TIN or BIN is
                                                  missing

  R05                     Delivery                Promised delivery is
                                                  later than 45 days
                                                  after the PO
  -----------------------------------------------------------------------

Price formula:

``` text
rejection_threshold = maximum_unit_price * 1.03
REJECT when quoted_unit_price > rejection_threshold
```

Exactly 3% above the maximum is not a rejection under this rule.

## 5.2 Human-review rules

If no rejection condition is established, mark the document
`NEEDS A PERSON TO CHECK` if any of these conditions apply:

  -----------------------------------------------------------------------
  Code                    Rule                    Review condition
  ----------------------- ----------------------- -----------------------
  H01                     Unit price              Above the maximum
                                                  price, but no more than
                                                  3% above it

  H02                     Quantity                Difference from
                                                  requested quantity is
                                                  greater than 5%

  H03                     Payment terms           Unclear or outside
                                                  30--60 days after
                                                  delivery

  H04                     Delivery                Promised delivery is
                                                  31--45 days

  H05                     VAT                     15% VAT is not shown
                                                  separately

  H06                     Arithmetic              Line total or subtotal
                                                  does not add up

  H07                     Quotation validity      Validity is less than
                                                  30 days

  H08                     Uncertainty             Important extracted
                                                  value is missing,
                                                  unsupported, or
                                                  conflicting and no
                                                  rejection is
                                                  established
  -----------------------------------------------------------------------

Quantity formula:

``` text
difference_percent =
    abs(quoted_quantity - requested_quantity)
    / requested_quantity * 100
```

Review when `difference_percent > 5`.

## 5.3 Approval rule

Approve only when:

-   No rejection rule is triggered.
-   No human-review rule is triggered.
-   Required values are present and verified.
-   The evidence supports the extracted values.
-   All applicable comparisons and calculations pass.

## 5.4 Decision priority

The priority is:

1.  `REJECT`
2.  `NEEDS A PERSON TO CHECK`
3.  `APPROVE`

If both rejection and review findings exist, the automated decision is
`REJECT`. Keep all findings in the result so the reviewer can see every
issue.

## 5.5 Boundary conditions

  Example                                   Expected result for that rule
  ----------------------------------------- -------------------------------
  Price equals maximum                      Pass
  Price is exactly 3% above maximum         Human review
  Price is 3.01% above maximum              Reject
  Advance payment is exactly 20%            Pass
  Advance payment is 20.01%                 Reject
  Quantity difference is exactly 5%         Pass
  Quantity difference is greater than 5%    Human review
  Delivery is 30 days                       Pass
  Delivery is 31--45 days                   Human review
  Delivery is more than 45 days             Reject
  Penalty is exactly 0.5% per week          Pass
  Penalty is below 0.5% per week            Reject
  Quotation validity is exactly 30 days     Pass
  Quotation validity is less than 30 days   Human review

Use `Decimal` for money and percentage calculations instead of binary
floating-point arithmetic.

## 5.6 Business-rule assumptions requiring confirmation

Before final implementation, inspect the supplied company rules and
sample files. Confirm:

-   Whether both TIN and BIN must always be present. The wording "TIN or
    BIN missing" is interpreted here as either missing identifier
    causing rejection.
-   How to calculate penalty percentage if the contract uses a different
    period or base amount.
-   How payment terms are represented and measured from the delivery
    date.
-   Whether VAT must be exactly 15% and separately displayed as a
    distinct amount.
-   How dates are calculated if the document provides calendar dates
    instead of a number of days.

Do not silently invent a policy for an ambiguous case. Record the
assumption and route uncertain cases to human review.

------------------------------------------------------------------------

# 6. End-to-End System Workflow

``` mermaid
flowchart TD
    A[Next.js UI] --> B[FastAPI API]
    B --> C[Create Evaluation Batch]
    C --> D[Upload PDFs, CSV and MD]
    D --> E[Validate Input Files]
    E --> F[Parse Purchase Request]
    E --> G[Load Company Rules]
    E --> H[Process Each Supplier PDF]
    H --> I[Extract PDF Text by Page]
    I --> J{Text readable?}
    J -->|No| K[OCR fallback]
    J -->|Yes| L[Structured source text]
    K --> L
    L --> M[LLM structured extraction]
    M --> N[Pydantic validation]
    N --> O[Evidence verification]
    O --> P[Purchase Request comparison]
    P --> Q[Python rule engine]
    Q --> R[Decision priority]
    R --> S[Save results in Neon]
    S --> T[Results dashboard]
```

Each supplier document follows the same workflow independently. The
batch is complete only when every document has a terminal state:
completed or failed.

------------------------------------------------------------------------

# 7. LangGraph Workflow Design

## 7.1 Required nodes

  -----------------------------------------------------------------------
  Node                                Purpose
  ----------------------------------- -----------------------------------
  `load_document`                     Load one supplier PDF and its batch
                                      context

  `extract_text`                      Extract page-by-page text

  `ocr_fallback`                      Read scanned pages when normal
                                      extraction is insufficient

  `extract_information`               Ask the LLM for structured fields

  `validate_schema`                   Validate the returned data with
                                      Pydantic

  `verify_evidence`                   Check that evidence supports
                                      extracted values

  `compare_purchase_request`          Match supplier item and values with
                                      the PR

  `validate_company_rules`            Execute deterministic Python rules

  `make_decision`                     Apply decision priority

  `save_result`                       Persist the complete result
  -----------------------------------------------------------------------

## 7.2 Workflow state

Keep the state small and typed. Store references and structured data,
not unnecessary duplicate copies of large PDF files.

``` python
from typing import TypedDict, Any

class SupplierEvaluationState(TypedDict, total=False):
    batch_id: str
    document_id: str
    filename: str

    pages: list[dict[str, Any]]
    extracted_data: dict[str, Any]
    evidence: list[dict[str, Any]]

    purchase_request_item: dict[str, Any]
    validation_results: list[dict[str, Any]]

    reject_flags: list[dict[str, Any]]
    review_flags: list[dict[str, Any]]

    final_decision: str
    processing_status: str
    errors: list[str]
```

## 7.3 Routing requirements

-   Invalid input file: stop that document and record failure.
-   Scanned page: run OCR fallback for that page.
-   Invalid LLM schema: retry a limited number of times.
-   Evidence not verified: mark the field unverified and add a review
    finding.
-   Explicit rejection condition: preserve the rejection finding.
-   Database save failure: do not mark the document completed.
-   Never approve an incomplete evaluation.

Use a fixed graph. Do not let the LLM choose which business rules to
run.

------------------------------------------------------------------------

# 8. Extraction Data Model

Use Pydantic models to define the exact shape expected from the LLM.

Example beginner-friendly model:

``` python
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class Evidence(BaseModel):
    field: str
    exact_text: str
    page: int = Field(ge=1)

class SupplierExtraction(BaseModel):
    supplier_name: Optional[str] = None
    supplier_tin: Optional[str] = None
    supplier_bin: Optional[str] = None

    item_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    line_total: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None

    currency: Optional[str] = None
    vat_amount: Optional[Decimal] = None
    vat_percentage: Optional[Decimal] = None

    delivery_days: Optional[int] = None
    advance_payment_percentage: Optional[Decimal] = None
    payment_terms: Optional[str] = None

    late_penalty_text: Optional[str] = None
    late_penalty_percentage: Optional[Decimal] = None
    late_penalty_period: Optional[str] = None

    quotation_validity_days: Optional[int] = None
    evidence: list[Evidence] = []
```

Implementation notes:

-   Use `Field(default_factory=list)` for mutable list defaults in
    production code.
-   If a value is not in the document, return `None`.
-   Do not use a default numeric value such as `0` to represent missing
    data.
-   Keep the original text and normalized value separately.
-   Extend the schema only after inspecting the actual sample documents.

------------------------------------------------------------------------

# 9. Evidence Verification

Every important extracted field should include:

``` json
{
  "field": "unit_price",
  "value": "4500.00",
  "exact_text": "Unit Price: BDT 4,500",
  "page": 1,
  "verification_status": "VERIFIED"
}
```

Verification requirements:

1.  The evidence must be taken from the extracted source page.
2.  The quoted text must match the source text.
3.  The page number must exist.
4.  The evidence must support the extracted value.
5.  If the text is absent, contradictory, or insufficient, mark it
    `UNVERIFIED`.
6.  Do not treat an LLM-provided evidence quote as verified merely
    because the LLM returned it.

For scanned PDFs, OCR text can contain mistakes. Keep the OCR source and
flag low-confidence or ambiguous values for human review.

------------------------------------------------------------------------

# 10. Beginner-Friendly Rule Engine Structure

Keep each rule in a small function. This makes the code easier to
understand, test, reuse, and debug.

Suggested files:

``` text
backend/app/validators/
├── __init__.py
├── price.py
├── quantity.py
├── payment.py
├── delivery.py
├── contract.py
├── arithmetic.py
└── decision.py
```

Example result format:

``` python
def create_finding(
    rule_code: str,
    status: str,
    message: str,
    actual_value=None,
    expected_value=None,
):
    return {
        "rule_code": rule_code,
        "status": status,
        "message": message,
        "actual_value": actual_value,
        "expected_value": expected_value,
    }
```

Example price validator:

``` python
from decimal import Decimal

def check_unit_price(
    quoted_price: Decimal,
    maximum_price: Decimal,
):
    if quoted_price is None or maximum_price is None:
        return "UNVERIFIED"

    if quoted_price > maximum_price * Decimal("1.03"):
        return "REJECT"

    if quoted_price > maximum_price:
        return "NEEDS_REVIEW"

    return "PASS"
```

Example quantity validator:

``` python
from decimal import Decimal

def check_quantity(
    quoted_quantity: Decimal,
    requested_quantity: Decimal,
):
    if quoted_quantity is None or requested_quantity is None:
        return "UNVERIFIED"

    if requested_quantity <= 0:
        return "UNVERIFIED"

    difference = (
        abs(quoted_quantity - requested_quantity)
        / requested_quantity
    ) * Decimal("100")

    if difference > Decimal("5"):
        return "NEEDS_REVIEW"

    return "PASS"
```

Example decision function:

``` python
def make_decision(reject_flags, review_flags):
    if reject_flags:
        return "REJECT"

    if review_flags:
        return "NEEDS A PERSON TO CHECK"

    return "APPROVE"
```

The production decision function must also receive extraction errors and
unverified required fields. Those must prevent approval and normally add
a human-review finding unless an independent rejection rule applies.

------------------------------------------------------------------------

# 11. Database Design --- Neon PostgreSQL

## 11.1 Connection

Create a Neon PostgreSQL project and copy its connection string into the
backend environment file.

Example:

``` env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Never put the database connection string in frontend code or commit it
to GitHub.

Use SQLAlchemy for database access and Alembic for migrations.

## 11.2 Tables

### `evaluation_batches`

Stores each evaluation session.

  Column            Type
  ----------------- ---------------------
  id                UUID, primary key
  name              VARCHAR
  status            VARCHAR
  total_documents   INTEGER
  created_at        TIMESTAMP
  completed_at      TIMESTAMP, nullable

### `supplier_documents`

Stores uploaded PDF metadata.

  Column              Type
  ------------------- -------------------
  id                  UUID, primary key
  batch_id            UUID, foreign key
  filename            VARCHAR
  storage_path        TEXT
  supplier_name       VARCHAR, nullable
  processing_status   VARCHAR
  created_at          TIMESTAMP

### `purchase_requests`

Stores normalized CSV rows.

  Column               Type
  -------------------- -------------------
  id                   UUID, primary key
  batch_id             UUID, foreign key
  item_name            VARCHAR
  requested_quantity   NUMERIC
  max_unit_price       NUMERIC
  currency             VARCHAR, nullable

### `extraction_results`

Stores structured LLM output.

  Column              Type
  ------------------- -------------------
  id                  UUID, primary key
  document_id         UUID, foreign key
  extracted_data      JSONB
  extraction_status   VARCHAR
  model_name          VARCHAR
  created_at          TIMESTAMP

### `evidence_records`

Stores supporting evidence.

  Column                Type
  --------------------- -------------------
  id                    UUID, primary key
  document_id           UUID, foreign key
  field_name            VARCHAR
  extracted_value       JSONB
  exact_text            TEXT
  page_number           INTEGER
  verification_status   VARCHAR

### `validation_results`

Stores each rule outcome.

  Column           Type
  ---------------- -------------------
  id               UUID, primary key
  document_id      UUID, foreign key
  rule_code        VARCHAR
  rule_category    VARCHAR
  status           VARCHAR
  expected_value   JSONB
  actual_value     JSONB
  evidence_id      UUID, nullable
  message          TEXT

### `evaluation_decisions`

Stores the automated final decision.

  Column        Type
  ------------- -------------------
  id            UUID, primary key
  document_id   UUID, foreign key
  decision      VARCHAR
  reasons       JSONB
  created_at    TIMESTAMP

### `human_reviews`

Stores human review notes.

  Column          Type
  --------------- ---------------------
  id              UUID, primary key
  document_id     UUID, foreign key
  reviewer_name   VARCHAR
  review_status   VARCHAR
  review_note     TEXT
  reviewed_at     TIMESTAMP, nullable

## 11.3 Database requirements

-   Use UUID primary keys.
-   Add foreign keys and appropriate indexes.
-   Use JSONB for flexible extracted data and evidence.
-   Use database transactions when saving a completed evaluation.
-   Use Alembic migrations.
-   Preserve the original automated decision when a human adds a review
    note.
-   Do not store large PDF binary data directly in PostgreSQL for this
    project. Store files locally for the demo and save their storage
    paths in the database.
-   Clearly document that local file paths are suitable for a local
    demo, not a multi-server production deployment.

------------------------------------------------------------------------

# 12. Backend API Design

Base path: `/api/v1`

  Method   Endpoint                                 Purpose
  -------- ---------------------------------------- ------------------------------
  POST     `/batches`                               Create an evaluation batch
  GET      `/batches`                               List batches
  GET      `/batches/{batch_id}`                    Get batch details and status
  POST     `/batches/{batch_id}/upload`             Upload PDFs, CSV, and MD
  POST     `/batches/{batch_id}/process`            Start evaluation
  GET      `/batches/{batch_id}/results`            Get supplier results
  GET      `/documents/{document_id}`               Get supplier details
  GET      `/documents/{document_id}/validations`   Get rule results
  GET      `/documents/{document_id}/evidence`      Get evidence
  POST     `/documents/{document_id}/reviews`       Save a human review note
  GET      `/documents/{document_id}/reviews`       Get review history

FastAPI Swagger must be available at `/docs`.

Use clear HTTP status codes and a consistent error response format. Do
not return stack traces or secrets to the frontend.

------------------------------------------------------------------------

# 13. Frontend Requirements

## 13.1 Pages

### Dashboard

Display:

-   Total batches.
-   Total documents.
-   Approved count.
-   Rejected count.
-   Needs-review count.
-   Failed count.
-   Recent batches.

### New Evaluation

Provide:

-   Batch name.
-   Multiple PDF upload.
-   Purchase Request CSV upload.
-   Company Rules MD upload.
-   File validation feedback.
-   Start evaluation action.

### Processing

Display each supplier's current stage:

-   Uploaded
-   Extracting text
-   Extracting information
-   Validating data
-   Checking evidence
-   Comparing purchase request
-   Applying rules
-   Completed
-   Failed

### Results

Display:

-   Supplier name.
-   Filename.
-   Item.
-   Quantity.
-   Unit price.
-   Final decision.
-   Number of findings.
-   Link to details.

Allow filtering by decision and processing status.

### Supplier Details

Display:

-   Supplier details.
-   Extracted quotation values.
-   Contract terms.
-   Purchase Request comparison.
-   Rule-by-rule outcomes.
-   Exact evidence and page number.
-   Automated decision and reasons.

### Human Review

Display pending review items. Allow a reviewer to add a note and mark
the review record completed. Preserve the automated decision separately.

## 13.2 UI principles

-   Keep the UI simple and professional.
-   Use clear status labels.
-   Include loading, empty, success, and error states.
-   Never show sample or hardcoded results as real evaluation output.
-   Show the original PDF or a page reference beside its evidence when
    practical.

------------------------------------------------------------------------

# 14. Reusable and Beginner-Friendly Code Standards

This project must be written for a developer who is learning Python
backend development and LangGraph.

## 14.1 General rules

1.  Use clear variable and function names.
2.  Keep functions small and focused on one task.
3.  Prefer simple code over unnecessary abstractions.
4.  Add type hints to function parameters and return values.
5.  Add short docstrings to important functions.
6.  Use Pydantic for API and extraction schemas.
7.  Keep business rules separate from API routes.
8.  Keep database queries separate from business logic.
9.  Avoid duplicate validation logic.
10. Do not create a generic framework when a simple reusable function is
    enough.
11. Add comments to explain non-obvious logic, not every line.
12. Do not put the entire application in one file.

## 14.2 Reusable structure

Use this responsibility separation:

  Layer        Responsibility                        Example
  ------------ ------------------------------------- --------------------------
  API route    Receive request and return response   `batches.py`
  Schema       Validate input/output structure       `schemas.py`
  Service      Coordinate a use case                 `evaluation_service.py`
  Repository   Read/write database records           `document_repository.py`
  Extraction   Read document and call LLM            `llm_extractor.py`
  Validator    Apply one business rule               `price.py`
  Workflow     Control processing order              `graph.py`
  Model        Define database tables                `models.py`

## 14.3 Reusable rule function pattern

Each rule should return a consistent finding structure. Do not make each
validator return a different shape.

``` python
def build_validation_result(
    rule_code: str,
    status: str,
    message: str,
    actual_value=None,
    expected_value=None,
):
    return {
        "rule_code": rule_code,
        "status": status,
        "message": message,
        "actual_value": actual_value,
        "expected_value": expected_value,
    }
```

Then each validator can reuse this function.

## 14.4 Reusable service pattern

A service should coordinate operations, not contain every implementation
detail.

Example:

``` python
class EvaluationService:
    def __init__(self, document_repository, workflow):
        self.document_repository = document_repository
        self.workflow = workflow

    async def evaluate_document(self, document_id: str):
        document = await self.document_repository.get_by_id(
            document_id
        )

        if document is None:
            raise ValueError("Document not found")

        result = await self.workflow.ainvoke({
            "document_id": document_id
        })

        return result
```

This is an illustrative pattern. Match the method names and async
behavior to the actual repository and workflow implementation.

## 14.5 Beginner-friendly explanation requirement

When generating code or documentation:

-   Explain what each module does.
-   Explain how data moves between modules.
-   Show how to run each part.
-   Include example requests and responses.
-   Explain important Python and LangGraph concepts in simple language.
-   Avoid advanced patterns unless they solve a real project
    requirement.

------------------------------------------------------------------------

# 15. Suggested Repository Structure

Use a single GitHub repository:

``` text
supplier-document-checker/
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── upload/
│   │   ├── results/
│   │   ├── documents/
│   │   └── reviews/
│   ├── components/
│   ├── services/
│   ├── types/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── batches.py
│   │   │   ├── documents.py
│   │   │   └── reviews.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── schemas/
│   │   │   ├── extraction.py
│   │   │   ├── batch.py
│   │   │   └── evaluation.py
│   │   ├── extraction/
│   │   │   ├── pdf_extractor.py
│   │   │   ├── ocr_extractor.py
│   │   │   └── llm_extractor.py
│   │   ├── workflow/
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   └── state.py
│   │   ├── validators/
│   │   │   ├── common.py
│   │   │   ├── price.py
│   │   │   ├── quantity.py
│   │   │   ├── payment.py
│   │   │   ├── delivery.py
│   │   │   ├── contract.py
│   │   │   ├── arithmetic.py
│   │   │   └── decision.py
│   │   ├── models/
│   │   │   ├── batch.py
│   │   │   ├── document.py
│   │   │   ├── evidence.py
│   │   │   └── evaluation.py
│   │   ├── repositories/
│   │   ├── services/
│   │   └── database/
│   │       └── connection.py
│   ├── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── requirements.txt
│   └── alembic.ini
│
├── sample-data/
├── docs/
│   ├── architecture.md
│   └── evaluation-report.md
├── .env.example
├── .gitignore
└── README.md
```

Create a module only when it has a clear responsibility. The structure
is a guide; do not add empty files just to match it.

------------------------------------------------------------------------

# 16. Environment Variables

Backend `.env`:

``` env
OPENAI_API_KEY=replace_with_your_key
OPENAI_MODEL=replace_with_supported_model
DATABASE_URL=replace_with_neon_connection_string

MAX_FILE_SIZE_MB=20
MAX_PDF_PAGES=100
MAX_EXTRACTION_RETRIES=2
UPLOAD_DIRECTORY=uploads
```

Frontend `.env.local`:

``` env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Add `.env` and `.env.local` to `.gitignore`. Commit only `.env.example`
with placeholder values.

------------------------------------------------------------------------

# 17. Testing Plan

## 17.1 Unit tests

Use Pytest to test each rule independently.

Required cases:

-   Price equals maximum.
-   Price exactly 3% above maximum.
-   Price more than 3% above maximum.
-   Advance payment exactly 20%.
-   Advance payment above 20%.
-   Missing TIN.
-   Missing BIN.
-   Missing penalty clause.
-   Penalty exactly 0.5%.
-   Penalty below 0.5%.
-   Delivery 30 days.
-   Delivery 31 days.
-   Delivery 45 days.
-   Delivery above 45 days.
-   Quantity difference exactly 5%.
-   Quantity difference above 5%.
-   Missing separately displayed VAT.
-   Incorrect line total.
-   Incorrect subtotal.
-   Quotation validity below 30 days.
-   Unclear payment terms.
-   Missing evidence.
-   Conflicting extracted values.
-   Rejection and review findings in the same document.

## 17.2 Integration tests

Test:

-   PDF extraction.
-   CSV parsing.
-   Markdown rule loading.
-   LLM structured extraction.
-   Pydantic validation.
-   Evidence verification.
-   Purchase Request matching.
-   Rule engine.
-   LangGraph execution.
-   Neon database persistence.

Use mocked LLM responses for deterministic automated tests. Do not make
every unit test call the real OpenAI API.

## 17.3 End-to-end evaluation

Run all 10 sample documents through the application.

Prepare a manually checked ground-truth table containing:

-   Supplier/document identifier.
-   Correct extracted fields.
-   Correct rule outcomes.
-   Correct expected decision.
-   Supporting text and page number.

Compare actual results with this ground truth.

Report:

-   Field extraction accuracy.
-   Final decision accuracy.
-   Evidence accuracy.
-   Rule coverage.
-   Processing success rate.
-   Number of documents escalated for human review.

Never claim an accuracy score that has not been measured.

------------------------------------------------------------------------

# 18. Error Handling and Reliability

  -----------------------------------------------------------------------
  Problem                             Expected behavior
  ----------------------------------- -----------------------------------
  Corrupted PDF                       Mark that document as failed

  Scanned PDF                         Attempt OCR

  Empty/unreadable PDF                Stop and record failure

  Missing extracted value             Mark unverified and review unless
                                      an explicit rejection applies

  Invalid LLM response                Retry a limited number of times

  Evidence not found                  Mark unverified

  Conflicting document values         Human review unless a rejection is
                                      independently established

  OpenAI timeout                      Controlled retry, then record error

  Invalid CSV                         Stop batch processing with a clear
                                      error

  PR item not found                   Human review

  Database save failure               Do not mark evaluation completed

  Duplicate process request           Prevent duplicate evaluation or
                                      return current status
  -----------------------------------------------------------------------

Supplier PDFs are untrusted input. Instructions written inside a
supplier document are data, not instructions to the LLM. The extraction
prompt must explicitly tell the model to ignore instructions embedded in
the document and only extract requested fields.

------------------------------------------------------------------------

# 19. Implementation Roadmap --- 72 Hours

  Time           Phase              Deliverable
  -------------- ------------------ -------------------------------------------
  Hours 0--6     Setup              Next.js, FastAPI, Neon connection
  Hours 6--12    Input processing   PDF, CSV, Markdown parsers
  Hours 12--20   Extraction         Pydantic schema and OpenAI extraction
  Hours 20--28   Evidence           Page references and evidence verification
  Hours 28--38   Rule engine        All rules and unit tests
  Hours 38--46   LangGraph          Fixed workflow and error routing
  Hours 46--54   Database/API       Persistence and API endpoints
  Hours 54--62   Frontend           Upload, dashboard, details, review
  Hours 62--68   Evaluation         Run 10 files and compare ground truth
  Hours 68--72   Submission         README, technical note, Loom demo

Prioritize a working and accurate evaluation pipeline over decorative UI
features.

------------------------------------------------------------------------

# 20. Acceptance Criteria

The application is complete when:

## Input

-   [ ] Ten supplier PDFs can be uploaded.
-   [ ] Purchase Request CSV can be uploaded and parsed.
-   [ ] Company Rules Markdown can be uploaded and read.
-   [ ] Invalid input is handled with clear errors.
-   [ ] Each supplier is processed independently.

## Extraction

-   [ ] Supplier information is extracted.
-   [ ] Quotation values are extracted.
-   [ ] Contract terms are extracted.
-   [ ] Missing values remain null.
-   [ ] Pydantic validates structured output.
-   [ ] Evidence includes exact text and page number.
-   [ ] Unsupported evidence is marked unverified.

## Rules and decisions

-   [ ] Every rejection rule is implemented.
-   [ ] Every human-review rule is implemented.
-   [ ] Boundary cases are tested.
-   [ ] Reject has priority over human review.
-   [ ] Incomplete evaluations cannot be approved.
-   [ ] Every decision has traceable reasons.

## Backend and database

-   [ ] FastAPI endpoints work.
-   [ ] Swagger documentation is available.
-   [ ] Neon PostgreSQL is connected.
-   [ ] Alembic migrations run successfully.
-   [ ] Results and evidence are persisted.

## Frontend

-   [ ] Upload page works.
-   [ ] Processing status is visible.
-   [ ] Results dashboard works.
-   [ ] Supplier details show findings and evidence.
-   [ ] Human-review notes can be recorded.

## Evaluation

-   [ ] All 10 sample documents are evaluated.
-   [ ] Actual results are compared with ground truth.
-   [ ] Evaluation metrics are documented.
-   [ ] Unit and integration tests are included.
-   [ ] README explains setup and execution.

------------------------------------------------------------------------

# 21. README Requirements

The final repository README must include:

1.  Project overview.
2.  Main features.
3.  Technology stack.
4.  Architecture diagram.
5.  Folder structure.
6.  Prerequisites.
7.  Backend setup commands.
8.  Frontend setup commands.
9.  Neon database setup.
10. Environment variable setup.
11. Database migration commands.
12. How to run backend and frontend locally.
13. How to upload and evaluate the sample files.
14. How to run tests.
15. Known limitations.
16. Evaluation results.

Document the actual commands used by the project. Do not include
commands for Docker or CI/CD.

------------------------------------------------------------------------

# 22. Final Engineering Principles

The implementation must follow these principles:

-   **LLM extracts; Python decides.**
-   **LangGraph orchestrates a fixed workflow.**
-   **Pydantic validates structured information.**
-   **Evidence supports every important finding.**
-   **Neon PostgreSQL stores results and audit information.**
-   **Uncertainty goes to human review.**
-   **No missing value is guessed.**
-   **Reusable functions are preferred over duplicated code.**
-   **Beginner-friendly code is preferred over unnecessary
    abstraction.**
-   **A failed or incomplete evaluation must never become an approval.**

The goal is not to build the largest AI application. The goal is to
build a small, reliable, explainable, testable supplier-document
verification system that correctly evaluates the 10 provided sample
documents.
