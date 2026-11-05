# Evaluation Report

Measured on 2026-11-05 with model `gemini-3.6-flash` (batch `02adb287-6974-4085-ab3c-9b8639dbb51f`).
All numbers below were measured by `python -m scripts.evaluate_samples` against
`backend/evaluation/ground_truth.json`, which was checked by hand from the PDFs.

## Summary

| Metric | Result |
|---|---|
| Final decision accuracy | 10/10 (100.0%) |
| Field extraction accuracy | 240/240 (100.0%) |
| Evidence accuracy (verified, correct page) | 194/194 (100.0%) |
| Rule outcome accuracy | 120/120 (100.0%) |
| Rule coverage (rule codes executed) | 13/13 (H01, H02, H03, H04, H05, H06, H07, H08, R01, R02, R03, R04, R05) |
| Processing success rate | 10/10 (100.0%) |
| Documents escalated to a person | 3 |

## Per document

| Document | Expected | Actual | Correct | Fields | Evidence | Rules |
|---|---|---|---|---|---|---|
| supplier-pack-01.pdf | APPROVE | APPROVE | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-02.pdf | APPROVE | APPROVE | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-03.pdf | REJECT | REJECT | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-04.pdf | NEEDS A PERSON TO CHECK | NEEDS A PERSON TO CHECK | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-05.pdf | REJECT | REJECT | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-06.pdf | REJECT | REJECT | yes | 24/24 | 19/19 | 12/12 |
| supplier-pack-07.pdf | NEEDS A PERSON TO CHECK | NEEDS A PERSON TO CHECK | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-08.pdf | REJECT | REJECT | yes | 24/24 | 18/18 | 12/12 |
| supplier-pack-09.pdf | NEEDS A PERSON TO CHECK | NEEDS A PERSON TO CHECK | yes | 24/24 | 20/20 | 12/12 |
| supplier-pack-10.pdf | REJECT | REJECT | yes | 24/24 | 17/17 | 12/12 |

## Field differences

None.
