"""The full HTTP flow, using an in-memory SQLite database and the fake LLM."""

from tests.conftest import SAMPLE_DATA, SAMPLE_PDFS

API = "/api/v1"


def sample_files() -> list[tuple]:
    files = [("files", (path.name, path.read_bytes(), "application/pdf")) for path in SAMPLE_PDFS]
    files.append(("files", ("purchase-request.csv", (SAMPLE_DATA / "purchase-request.csv").read_bytes(), "text/csv")))
    files.append(("files", ("company-rules.md", (SAMPLE_DATA / "company-rules.md").read_bytes(), "text/markdown")))
    return files


def create_batch(client) -> str:
    response = client.post(f"{API}/batches", json={"name": "Test batch"})
    assert response.status_code == 201
    return response.json()["id"]


def test_full_evaluation_flow(client, ground_truth):
    batch_id = create_batch(client)

    upload = client.post(f"{API}/batches/{batch_id}/upload", files=sample_files())
    assert upload.status_code == 200, upload.text
    assert upload.json()["batch"]["status"] == "READY"
    assert upload.json()["batch"]["total_documents"] == 10

    # TestClient runs background tasks before returning, so processing is finished here.
    process = client.post(f"{API}/batches/{batch_id}/process")
    assert process.status_code == 202

    batch = client.get(f"{API}/batches/{batch_id}").json()
    assert batch["status"] == "COMPLETED"

    results = client.get(f"{API}/batches/{batch_id}/results").json()
    decisions = {row["filename"]: row["decision"] for row in results}
    assert decisions == {name: truth["expected_decision"] for name, truth in ground_truth.items()}

    rejected = client.get(f"{API}/batches/{batch_id}/results", params={"decision": "REJECT"}).json()
    assert len(rejected) == 5

    # Supplier details, rule results and evidence
    document_id = next(row["document_id"] for row in results if row["filename"] == "supplier-pack-03.pdf")
    detail = client.get(f"{API}/documents/{document_id}").json()
    assert detail["decision"] == "REJECT"
    assert detail["purchase_request_item"]["max_unit_price"] == "210.0000"
    assert detail["decision_reasons"][0]["rule_code"] == "R01"

    validations = client.get(f"{API}/documents/{document_id}/validations").json()
    r01 = next(v for v in validations if v["rule_code"] == "R01")
    assert r01["status"] == "REJECT"
    assert r01["evidence"]["exact_text"] == "cone 229.00" and r01["evidence"]["page_number"] == 1
    assert "3%" in r01["rule_text"]

    evidence = client.get(f"{API}/documents/{document_id}/evidence").json()
    assert all(e["verification_status"] in ("VERIFIED", "NOT_FOUND") for e in evidence)

    pdf = client.get(f"{API}/documents/{document_id}/file")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    dashboard = client.get(f"{API}/dashboard").json()
    assert (dashboard["approved"], dashboard["rejected"], dashboard["needs_review"], dashboard["failed"]) == (2, 5, 3, 0)


def test_human_review_keeps_automated_decision(client):
    batch_id = create_batch(client)
    client.post(f"{API}/batches/{batch_id}/upload", files=sample_files())
    client.post(f"{API}/batches/{batch_id}/process")

    pending = client.get(f"{API}/reviews/pending").json()
    assert len(pending) == 3
    document_id = pending[0]["document_id"]

    review = client.post(
        f"{API}/documents/{document_id}/reviews",
        json={"reviewer_name": "Rahim", "review_status": "COMPLETED", "reviewer_decision": "APPROVE", "review_note": "Checked by phone."},
    )
    assert review.status_code == 201
    assert review.json()["reviewed_at"] is not None

    assert len(client.get(f"{API}/reviews/pending").json()) == 2
    assert client.get(f"{API}/documents/{document_id}").json()["decision"] == "NEEDS A PERSON TO CHECK"
    assert len(client.get(f"{API}/documents/{document_id}/reviews").json()) == 1


def test_duplicate_process_request_is_refused(client):
    batch_id = create_batch(client)
    client.post(f"{API}/batches/{batch_id}/upload", files=sample_files())
    client.post(f"{API}/batches/{batch_id}/process")
    second = client.post(f"{API}/batches/{batch_id}/process")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_PROCESSED"


def test_processing_requires_all_inputs(client):
    batch_id = create_batch(client)
    pdf = SAMPLE_PDFS[0]
    client.post(f"{API}/batches/{batch_id}/upload", files=[("files", (pdf.name, pdf.read_bytes(), "application/pdf"))])
    response = client.post(f"{API}/batches/{batch_id}/process")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BATCH_NOT_READY"


def test_invalid_upload_saves_nothing_and_explains_why(client):
    batch_id = create_batch(client)
    pdf = SAMPLE_PDFS[0]
    response = client.post(
        f"{API}/batches/{batch_id}/upload",
        files=[
            ("files", (pdf.name, pdf.read_bytes(), "application/pdf")),
            ("files", ("copy.pdf", pdf.read_bytes(), "application/pdf")),
            ("files", ("fake.pdf", b"not a pdf", "application/pdf")),
            ("files", ("purchase-request.csv", b"Item,Quantity\nA,10\n", "text/csv")),
        ],
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_FILES"
    assert {d["filename"] for d in error["details"]} == {"copy.pdf", "fake.pdf", "purchase-request.csv"}
    assert client.get(f"{API}/batches/{batch_id}").json()["total_documents"] == 0


def test_unknown_batch_returns_404_in_standard_format(client):
    response = client.get(f"{API}/batches/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BATCH_NOT_FOUND"
