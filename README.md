# Supplier Document Checker

A web app that reads supplier quotations (PDF), compares them with the company's
Purchase Request and company rules, and gives each document one answer:

- **APPROVE**: every rule passes and every important value is backed by text in the PDF.
- **REJECT**: at least one rejection rule is clearly broken.
- **NEEDS A PERSON TO CHECK**: nothing is clearly broken, but something is unclear,
  missing, unverified or triggers a review rule.

**The AI never decides.** The LLM only copies information out of the PDF. Python
checks that every copied value really appears on the page, then plain Python rules
make the decision. When the system is not sure, it asks a person.

---

## 1. Main features

- Upload many supplier PDFs, one Purchase Request CSV and one company-rules Markdown file.
- Files are checked by content (not just the filename): real PDF, readable, page limit, no duplicates.
- Page-by-page PDF text, with an OCR fallback for scanned pages (Gemini API, optional).
- Structured extraction with **OpenAI or Gemini** (one setting), validated by Pydantic, retried if the answer has the wrong shape.
- **Evidence verification**: each value must be found, word for word, on the page it cites.
- 13 company rules (R01-R05 reject, H01-H08 review) as small, tested Python functions.
- Every finding shows the exact quote and page number, with a link to the original PDF page.
- Live processing progress per document.
- Human review notes, saved next to (never replacing) the automated decision.
- Everything saved in Neon PostgreSQL; accuracy measured against a hand-checked ground truth.

## 2. Technology stack

| Area | Technology |
|---|---|
| Frontend | Next.js 16 + TypeScript + Tailwind CSS |
| Backend | Python 3.12 + FastAPI |
| Workflow | LangGraph (fixed steps) |
| LLM | OpenAI or Gemini API (extraction only, chosen by `LLM_PROVIDER`) |
| PDF text / OCR | PyMuPDF / Gemini API (scanned pages only) |
| Validation | Pydantic |
| Database | Neon PostgreSQL + SQLAlchemy + Alembic |
| Tests | Pytest |

## 3. Architecture

```mermaid
flowchart TD
    UI[Next.js UI] -->|REST /api/v1| API[FastAPI]
    API --> Upload[Validate files<br/>parse CSV, check rules MD]
    Upload --> DB[(Neon PostgreSQL)]
    API -->|background task| Batch[Run each PDF separately]
    Batch --> G

    subgraph G[LangGraph workflow - one supplier PDF]
        L[load_document] --> T[extract_text]
        T -->|page has no text| O[ocr_fallback]
        T --> E[extract_information<br/>OpenAI or Gemini]
        O --> E
        E --> S[validate_schema<br/>Pydantic]
        S -->|bad JSON, retry| E
        S --> V[verify_evidence]
        V --> P[compare_purchase_request]
        P --> R[validate_company_rules]
        R --> D[make_decision]
        D --> SV[save_result]
        L & T & O & E & S -->|fatal error| F[record_failure]
    end

    SV --> DB
    F --> DB
```

See [docs/architecture.md](docs/architecture.md) for how data moves between modules,
the design decisions, and the business-rule assumptions.

## 4. Folder structure

```text
supplier-document-checker/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, error handlers, CORS
│   │   ├── api/                 HTTP routes (thin: call a service, return the result)
│   │   ├── core/                settings (.env) and the shared error type
│   │   ├── inputs/              CSV parser, company-rules loader, upload file checks
│   │   ├── extraction/          PDF text, OCR, OpenAI prompt and extractor
│   │   ├── evidence/            checks that each quote is really in the PDF
│   │   ├── validators/          one small file per rule topic + decision + rule engine
│   │   ├── workflow/            LangGraph state, nodes and graph
│   │   ├── models/              database tables (SQLAlchemy)
│   │   ├── repositories/        database reads and writes
│   │   ├── services/            use cases: upload, evaluate, results, reviews
│   │   ├── schemas/             Pydantic shapes for the LLM and the API
│   │   └── database/            engine and transactions
│   ├── migrations/              Alembic migrations
│   ├── evaluation/              ground_truth.json + accuracy calculator
│   ├── scripts/evaluate_samples.py
│   ├── tests/unit, tests/integration
│   ├── requirements.txt, alembic.ini, .env.example
├── frontend/
│   ├── app/                     pages: dashboard, upload, results, documents, reviews
│   ├── components/  services/  hooks/  types/
├── sample-data/                 the 10 PDFs, purchase-request.csv, company-rules.md
└── docs/                        architecture.md, evaluation-report.md
```

## 5. Prerequisites

- **Python 3.12** (see the note below if you only have a newer Python)
- **Node.js 20+** and npm
- A free **Neon** account: https://neon.tech
- An LLM key: a **Gemini API key** (https://aistudio.google.com/apikey) or an **OpenAI API key**
  (https://platform.openai.com/api-keys, the account needs credits)
- Optional: a **Gemini API key** (https://aistudio.google.com/apikey), only needed for scanned PDFs
  (the sample PDFs have a text layer, so it is not used for them).

> **Python version note.** Some libraries (LangGraph's `zstandard` dependency) have no
> ready-made package for very new Python versions such as 3.15 and fail to install on
> Windows. The project therefore uses Python 3.12. If you do not have it, `uv` can
> download it for this project only, without changing your system Python:
>
> ```powershell
> python -m pip install --user uv
> python -m uv python install 3.12
> ```

## 6. Backend setup

All commands are for Windows PowerShell, run from the `backend` folder.

```powershell
cd backend

# Create the virtual environment (an isolated Python just for this project)
python -m uv venv .venv --python 3.12      # or: py -3.12 -m venv .venv

# Activate it (your prompt then starts with "(.venv)")
.venv\Scripts\Activate.ps1

# Install the libraries
python -m uv pip install -r requirements.txt   # or: pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run this once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 7. Neon database setup

1. Sign in at https://console.neon.tech and create a project (any name, nearest region).
2. On the project dashboard, click **Connect** and copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`
3. Change the start from `postgresql://` to **`postgresql+psycopg://`** (this tells
   SQLAlchemy to use the psycopg driver). Keep everything else the same.

## 8. Environment variables

```powershell
copy .env.example .env
notepad .env
```

Fill in at least:

| Variable | What to put |
|---|---|
| `LLM_PROVIDER` | `gemini`, `openai` or `deepseek`: which LLM extracts the information |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | for `deepseek`: your Modal server address (ending in `/v1`) and model name |
| `MODAL_PROXY_TOKEN_ID`, `MODAL_PROXY_TOKEN_SECRET` | for `deepseek`: the Modal proxy auth token (Modal dashboard) |
| `MODAL_ROUTING_AFFINITY_KEY` | for `deepseek`, optional: sent as the `Modal-Routing-Affinity-Key` header |
| `GEMINI_API_KEY` | your Gemini key (needed for `gemini`, and for reading scanned pages) |
| `GEMINI_MODEL` | Gemini model for extraction, default `gemini-3.6-flash` |
| `OPENAI_API_KEY` | your OpenAI key (needed for `openai`) |
| `OPENAI_MODEL` | OpenAI chat model with JSON mode, default `gpt-4.1-mini` |
| `DATABASE_URL` | the Neon string from step 7 (starting `postgresql+psycopg://`) |

The other values have sensible defaults (20 MB file limit, 100 pages, 2 LLM retries,
uploads stored in `backend/uploads`). `.env` is in `.gitignore`; never commit it.

Frontend (`frontend/.env.local`, already created from `.env.example`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## 9. Database migrations

```powershell
cd backend
.venv\Scripts\Activate.ps1
alembic upgrade head          # creates all tables in Neon
```

`alembic upgrade head --sql` prints the SQL without running it, if you want to read it first.

## 10. Run locally

Two terminals:

```powershell
# Terminal 1 - backend
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

```powershell
# Terminal 2 - frontend (first time: npm install)
cd frontend
npm install
npm run dev
```

> **"uvicorn is not recognized"?** The virtual environment is not active (PowerShell may have
> blocked `Activate.ps1`). Do not install anything: `uvicorn` is already in `.venv`. Either run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and activate again, or skip
> activation and call the project's Python directly:
>
> ```powershell
> cd backend
> .venv\Scripts\python -m uvicorn app.main:app --reload
> ```
>
> Avoid `python3 -m pip install ...` here: `python3` is your system Python, not the project's.

- App: http://localhost:3000
- Interactive API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 11. Evaluate the sample files

**In the browser:** open http://localhost:3000, click **New evaluation**, enter a name, select
the 10 PDFs from `sample-data/`, then `purchase-request.csv` and `company-rules.md`, and click
**Upload and start evaluation**. Watch each document move through the stages, then open
**Details** on any row to see each rule, the exact quote and the page link.

**From the command line (also measures accuracy):**

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m scripts.evaluate_samples
```

This creates a batch, runs all 10 documents with the real LLM chosen by `LLM_PROVIDER`, saves everything in
Neon, compares the results with `backend/evaluation/ground_truth.json`, and writes
`docs/evaluation-report.md`. To measure a batch you made in the UI instead:
`python -m scripts.evaluate_samples --batch-id <batch id>`.

### Example API calls

```powershell
# Create a batch
curl -X POST http://localhost:8000/api/v1/batches -H "Content-Type: application/json" -d '{\"name\": \"Demo\"}'
# -> {"id": "8f1c...", "status": "CREATED", "total_documents": 0, ...}

# Upload files (repeat -F for every file)
curl -F files=@../sample-data/supplier-pack-01.pdf -F files=@../sample-data/purchase-request.csv `
     -F files=@../sample-data/company-rules.md http://localhost:8000/api/v1/batches/8f1c.../upload

# Start and check results
curl -X POST http://localhost:8000/api/v1/batches/8f1c.../process
curl http://localhost:8000/api/v1/batches/8f1c.../results
# -> [{"filename": "supplier-pack-01.pdf", "decision": "APPROVE", "findings_count": 0, ...}]
```

Errors always have the same shape:

```json
{"error": {"code": "INVALID_FILES", "message": "Some files could not be accepted. Nothing was saved.",
           "details": [{"filename": "fake.pdf", "message": "is not a real PDF file (content does not start with %PDF-)."}]}}
```

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/batches` | Create an evaluation batch |
| GET | `/batches` | List batches |
| GET | `/batches/{id}` | Batch status and each document's stage |
| POST | `/batches/{id}/upload` | Upload PDFs, CSV and MD |
| POST | `/batches/{id}/process` | Start evaluation (409 if already started) |
| GET | `/batches/{id}/results?decision=&processing_status=` | Supplier results |
| GET | `/documents/{id}` | Supplier details and decision |
| GET | `/documents/{id}/validations` | Rule-by-rule outcomes with evidence |
| GET | `/documents/{id}/evidence` | All evidence records |
| GET | `/documents/{id}/file` | The original PDF |
| POST / GET | `/documents/{id}/reviews` | Add / list human review notes |
| GET | `/reviews/pending` | Documents waiting for a person |
| GET | `/dashboard` | Totals for the dashboard |

## 12. Run the tests

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```

The tests use a fake LLM (replaying the hand-checked answers) and an in-memory SQLite
database, so they are free, fast and need no keys. They cover every rule boundary in the PRD,
evidence verification, CSV/Markdown parsing, file validation, the full LangGraph workflow on
all 10 sample PDFs (including retries, OCR routing, corrupted PDFs and database failures), and
the HTTP API.

Two optional tests use the real services:

```powershell
$env:RUN_NEON_TESTS="1"; pytest -m neon        # writes and deletes one row in Neon
$env:RUN_OPENAI_TESTS="1"; pytest -m openai    # one real OpenAI extraction of supplier-pack-01
```

Frontend checks: `cd frontend; npm run lint; npm run build`.

## 13. Known limitations

- **Local file storage.** Uploaded PDFs are saved in `backend/uploads` and only their paths are
  in the database. That is fine for a local demo but not for several servers.
- **Background work runs inside the API process.** If the server restarts during processing,
  the batch stays `PROCESSING`. A real deployment would use a job queue.
- **One item per quotation.** Multi-line quotations go to a person (H08).
- **OCR is optional and always sent to a person.** Scanned pages need `GEMINI_API_KEY`, and
  any value read by OCR triggers human review because OCR can misread numbers.
- **No login.** Version 1 has no authentication, as agreed in the PRD.
- **Rule thresholds are in Python** (`validators/rule_catalog.py`). The uploaded Markdown is
  checked against them; a changed policy file is refused rather than silently applied.
- **Accuracy depends on the LLM.** Measured with `gemini-3.6-flash`: 10/10 on the samples. These are
  10 clean, one-page PDFs; real supplier documents will be messier. A busy Gemini model (503) is
  retried automatically; if it stays busy, the document fails and goes to a person.

## 14. Evaluation results

Measured on 2026-11-05 with `gemini-3.6-flash` (full report: [docs/evaluation-report.md](docs/evaluation-report.md)):

| Metric | Result |
|---|---|
| Final decision accuracy | 10/10 |
| Field extraction accuracy | 240/240 |
| Evidence accuracy | 194/194 |
| Rule outcome accuracy | 120/120 |
| Processing success rate | 10/10 |
| Escalated to a person | 3 (packs 04, 07, 09) |

The report is regenerated by `python -m scripts.evaluate_samples` and only contains measured numbers.

The hand-checked expected answers are:

| Pack | Expected | Reason |
|---|---|---|
| 01 | APPROVE | all rules pass |
| 02 | APPROVE | all rules pass |
| 03 | REJECT | R01 price 229.00 is 9.05% above max 210.00 |
| 04 | NEEDS A PERSON TO CHECK | H01 price 6.65 is 2.31% above max 6.50 |
| 05 | REJECT | R02 40% advance |
| 06 | REJECT | R03 no late-delivery penalty clause |
| 07 | NEEDS A PERSON TO CHECK | H02 quantity 16,500 vs 20,000 (17.5%) |
| 08 | REJECT | R04 no TIN/BIN |
| 09 | NEEDS A PERSON TO CHECK | H06 50,000 x 6.40 is not 322,000; H03 "30 to 90 days" |
| 10 | REJECT | R05 delivery 60 days (also H05 VAT not separate) |
