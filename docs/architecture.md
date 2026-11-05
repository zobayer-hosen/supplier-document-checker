# Architecture

## The one big idea

| Who | Does | Never does |
|---|---|---|
| LLM (OpenAI or Gemini) | Copies values and exact quotes out of the PDF text | Decides, calculates, chooses steps |
| Python evidence check | Confirms each quote is really on the cited page and contains the value | Trusts the LLM's quote blindly |
| Python rules | Apply company rules to **verified** values only | Use an unverified value |
| LangGraph | Runs the same fixed steps in the same order for every PDF | Let anything pick the next step |
| Neon | Stores inputs, every finding, evidence and decision | Store PDF bytes (only file paths) |

## How data moves

1. **Upload** (`api/batches.py` -> `services/upload_service.py` -> `inputs/*`)
   Each file is checked by content. The CSV is mapped from its real header names to
   `PurchaseRequestItem`. The rules Markdown is checked against `validators/rule_catalog.py`;
   the original wording of each rule is stored so the UI can show it. If any file is bad,
   nothing is saved.
2. **Process** (`services/evaluation_service.py`)
   The request marks the batch `PROCESSING` (a second request gets `409`), then a background
   task runs the LangGraph workflow once per PDF. One broken PDF cannot stop the others.
3. **Workflow** (`workflow/graph.py`, `workflow/nodes.py`). The state is a small `TypedDict`
   (`workflow/state.py`): file path, page texts, extracted data, evidence, findings, decision.
   - `extract_text`: PyMuPDF, page by page. Pages with almost no text are marked `needs_ocr`.
   - `ocr_fallback`: those pages only are rendered to PNG and transcribed by Gemini
     (`extraction/ocr_extractor.py`). Gemini copies text; it does not extract or decide.
   - `extract_information`: `OpenAIExtractor` or `GeminiExtractor` (`LLM_PROVIDER`), same prompt and JSON mode. The prompt (`extraction/prompts.py`) says the document is untrusted
     data, values must be copied as written, missing values are `null`, and every value needs a quote.
   - `validate_schema`: Pydantic `SupplierExtraction`. If invalid, the error is sent back to the
     LLM; after `MAX_EXTRACTION_RETRIES` the document is marked failed.
   - `verify_evidence`: each field becomes VERIFIED / UNVERIFIED / NOT_FOUND / CONFLICTING.
     Unverified values are replaced with `None` before the rules see them.
   - `compare_purchase_request`: match by item code, then by description; any mismatch is H08.
   - `validate_company_rules`: `validators/rule_engine.py` calls every rule function.
   - `make_decision`: REJECT > NEEDS A PERSON TO CHECK > APPROVE. Approval also requires that
     every rule code ran and there were no processing errors.
   - `save_result`: one database transaction. Only a successful save marks the document COMPLETED.
4. **Read** (`services/results_service.py`, `services/review_service.py`) turns records into API shapes.

**LangGraph in one sentence:** a graph is a list of named steps (nodes) plus arrows (edges);
each node gets the current state and returns only the keys it changed; conditional edges are
ordinary Python functions that look at the state and return the name of the next node.

## Business-rule assumptions (PRD section 5.6)

These were decided after reading the 10 samples. Anything uncertain goes to a person.

| Question | Decision |
|---|---|
| TIN and BIN | Both are required. Either missing -> REJECT (R04). "Missing" needs two signals: the LLM found nothing **and** the words TIN/BIN do not appear in the text. If they disagree -> person. |
| Penalty base and period | Must be a % of order (or contract) value. Weekly rate used as is; a daily rate is multiplied by 7; a monthly rate is not converted (-> person). No stated base (pack 08) -> person. |
| No penalty clause | REJECT only when the LLM found none **and** no penalty/delay wording exists in the text. |
| Payment terms | "within N days of/after delivery" = N days after delivery. Must be 30-60. A range ("30 to 90 days") or no reference to delivery is unclear -> person. |
| VAT | Must be shown as a separate amount at exactly 15%. Prices "VAT included" -> person (H05). VAT amount is also checked in H06. |
| Delivery and validity | "N days of PO" = N days after the PO. Weeks x 7. Months are not converted (-> person). |
| Unit price | Compared as written on the quotation, in the PR currency. 3% limit uses `max x 1.03`, with `Decimal`. |
| Arithmetic tolerance | 0.01 BDT, after rounding to 2 decimals. |

## Error handling

| Problem | What happens |
|---|---|
| Fake/corrupted/locked PDF, wrong type, too large, duplicate | Upload refused with one message per file; nothing saved |
| Bad CSV or rules file | Upload refused with the reason |
| PDF unreadable during processing | Document FAILED, others continue |
| Scanned page | OCR; OCR values always go to a person |
| LLM wrong shape | Retry with the error, then FAILED |
| LLM timeout / rate limit / overloaded | SDK retries with backoff, then FAILED with a clear message (for example "no credits left") |
| Quote not in PDF | Field UNVERIFIED -> H08 -> person |
| PR item not found | H08 -> person |
| Database save fails | Document FAILED, never COMPLETED |
| Unexpected server error | 500 with a generic message; stack trace only in the server log |

## Production notes

Local file storage and in-process background tasks are fine for this demo. For several
servers, store PDFs in object storage (for example S3) and run evaluations from a job queue.
