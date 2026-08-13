# PII redaction evaluation report

Two scorecards are kept apart:

1. **Attached document** — hand labels on prospectus pages 1, 5, 6, 39.
2. **Synthetic unit tests** — a small ticket-log snippet (SSN, card, DOB, IP,
   extra date/phone/IPv6 shapes). These numbers are **not** mixed into (1).

A predicted span is a true positive when it has the same type as a gold span
on the same page and the character offsets overlap by at least half of the
shorter span. Each occurrence counts once (not unique text).

If a denominator is zero, the metric is **N/A** (not 1.0).

## Attached document (prospectus sample pages)

No prospectus pages were scored (the file is not the labeled RHP sample).

- **Precision:** N/A
- **Recall:** N/A
- **F1:** N/A
- **Accuracy:** N/A
- **Scored:** false

## Synthetic unit tests

These rows test detector formats. They are not part of the PDF overall score.

- **Precision:** 1.000  (TP=21, FP=0)
- **Recall:** 1.000  (TP=21, FN=0)
- **F1:** 1.000
- **Accuracy:** 1.000

| Type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| address | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| company | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| credit_card | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| dob | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| email | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| ip | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| name | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| phone | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| ssn | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |

## Method

- Gold set: prospectus pages **1, 5, 6, 39** plus synthetic ticket snippets.
- Matching uses **page number + character offsets**, not unique (text, type) keys.
- Character-level accuracy: each character is PII or not from gold vs predicted spans.
- CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names
  were **not** labeled as PII.
- Scoring the attached document requires a prospectus fingerprint (known phrases
  on the labeled pages). Any other file, including a long unrelated PDF, is N/A.
- These document scores are for the labeled sample, not the full 130-page PDF.

## False positives / false negatives

Examples are masked so original PII is not written into the report.

