# PII Redaction Tool

A Python application that detects personally identifiable information (PII), replaces it with stable fake alternatives, and produces a redacted Word document. It accepts `.txt`, `.pdf`, and `.docx` input through either the command line or a FastAPI web interface.

The same detected value receives the same replacement throughout one document. DOCX processing preserves tables, headers, footers, text boxes, and run formatting where possible. Images are checked with Tesseract OCR; sensitive identity-document images are replaced with a clear placeholder while ordinary logos and images are retained.

## Supported PII

The tool covers all nine categories required by the assignment:

| PII category | Detection approach |
|---|---|
| Full names | Gazetteer and context cues such as `Contact Person`, `Dear`, and titles |
| Email addresses | Email pattern matching |
| Phone numbers | International, Indian, and common US formats |
| Company names | Gazetteer, company suffixes, and family-trust patterns |
| Physical addresses | Gazetteer plus Indian PIN, street, and basic US address patterns |
| SSNs | Hyphenated format or digits following an SSN label |
| Credit cards | 13–19 digits, Luhn validation, and card-related context |
| Dates of birth | Date patterns following `DOB`, `date of birth`, or `born` |
| IP addresses | Valid IPv4 and IPv6 addresses |

Order and ticket numbers are not treated as credit cards unless the number passes the Luhn check and appears in card-related context. CIN, PAN, DIN, monetary values, share counts, page numbers, and statute names are outside the selected PII policy.

## Installation

Python 3.12 or later is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

DOCX files containing images also require the Tesseract OCR binary:

```bash
# macOS
brew install tesseract

# Debian/Ubuntu
sudo apt-get install tesseract-ocr
```

If OCR is required but unavailable, the application stops with an explanatory error rather than silently leaving sensitive images unchanged.

## Command-line usage

Redact a Word document:

```bash
python main.py "input.docx" -o "output/redacted.docx"
```

Redact a PDF and create an evaluation report:

```bash
python main.py "input.pdf" -o "output/redacted.docx" --evaluate
```

Redact a ticket log:

```bash
python main.py "samples/ticket_log.txt" -o "output/ticket_log_redacted.docx"
```

## Web application

Start the FastAPI interface locally:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`, upload a supported file, and download the processed DOCX. Original uploaded PII is not included in API responses.

## Evaluation strategy

Ground-truth labels are stored in `data/gold_labels.json`. A predicted occurrence is counted as a true positive when it has the same PII category and page as a gold occurrence and their character spans overlap by at least half of the shorter span. Each occurrence is counted separately.

The report uses:

- **Precision:** `TP / (TP + FP)`
- **Recall:** `TP / (TP + FN)`
- **F1:** `2 × Precision × Recall / (Precision + Recall)`
- **Accuracy:** character-level agreement between PII and non-PII labels

The labelled prospectus evaluation covers selected PDF pages only. A DOCX is not scored against PDF character offsets, so its prospectus metrics are correctly reported as `N/A` with `Scored: false`. Synthetic labelled detector tests are reported separately and are not presented as full-document prospectus accuracy. When a metric has no valid denominator, it is reported as `N/A` rather than an invented score.

False-positive and false-negative examples are masked before being written to the report.

## Approach and trade-offs

The detector uses regular expressions and small gazetteers instead of a neural NER model. This keeps installation and execution simple and makes new PII categories easy to add, but it creates precision/recall trade-offs:

- Names without a known value or context cue may be missed.
- Broad title-case name matching is avoided because prospectus headings can look like names.
- Bare 10-digit values are not automatically treated as phones, which protects ticket and order identifiers.
- Credit-card detection requires both a valid Luhn checksum and card-related context.
- Dates are treated as dates of birth only when a DOB-related label is present.
- Address boundaries can occasionally be slightly longer or shorter than a hand-labelled span.

## Project structure

```text
redact/                 Detection, replacement, extraction, DOCX and evaluation logic
data/gazetteer.json     Assignment-specific names, companies and addresses
data/gold_labels.json   Labelled evaluation occurrences and synthetic cases
samples/ticket_log.txt  Synthetic text example
app.py                  FastAPI upload application
main.py                 Command-line entry point
start.py                Production server entry point
Dockerfile              Railway container with Python and Tesseract
```

Input prospectus files, user uploads, and generated outputs are intentionally excluded from version control to avoid publishing source PII or temporary processing artifacts. The processed DOCX and evaluation report should be shared separately using view-only links.

## Extending the tool

To support another PII category:

1. Add its detector to `redact/detectors.py` and register it in `DETECTORS`.
2. Add its fake-value generator to `redact/replacements.py`.
3. Add labelled examples to `data/gold_labels.json`.
4. Run the evaluation again and document any new false positives or false negatives.
