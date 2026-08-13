# PII Redaction Tool

This tool reads a PDF (the attached KSH International Red Herring Prospectus) or a `.txt` ticket log, finds personally identifiable information (PII), replaces each value with a **stable fake stand-in**, and writes a redacted Word file (`.docx`).

The same real value always becomes the same fake value in one run.

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Redact the prospectus and write the evaluation report:

```bash
python main.py samples/Red_Herring_Prospectus.pdf -o output/KSH_RHP_redacted.docx --evaluate
```

Redact the sample ticket log only:

```bash
python main.py samples/ticket_log.txt -o output/ticket_log_redacted.docx
```

Optional web UI:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`, upload a file, download the `.docx`. The API does **not** return original PII.

## Deploy

The web app is FastAPI (`app.py`). **Railway** is the better host for large PDFs. **Vercel** can run the same app as a Python function, with a 60-second time limit and a smaller upload cap.

### Railway

1. Push this repo to GitHub.
2. In [Railway](https://railway.app), **New Project → Deploy from GitHub repo**.
3. Railway uses the `Dockerfile` and binds to `$PORT`.
4. Open the public URL when the deploy finishes.

Optional: set `CORS_ORIGINS` if a separate frontend calls the API (comma-separated origins). Default is `*`.

### Vercel

1. Import the same GitHub repo at [vercel.com/new](https://vercel.com/new).
2. Vercel detects FastAPI from `requirements.txt` and uses `app:app` (`pyproject.toml`).
3. Deploy. The UI is served at `/`.

Vercel Hobby functions max out at **60 seconds** and about **4.5 MB** request bodies. Use Railway for the full prospectus PDF or other large files. Ticket logs and smaller PDFs are fine.

## Approach

Hybrid **regex + gazetteer**. There is no neural NER model.

| PII type | How it is found |
|---|---|
| Email | Pattern for `name@domain` |
| Phone | `+` country codes, Indian `+91`, US `(xxx) xxx-xxxx` |
| SSN | `123-45-6789` or unhyphenated `123456789` after the word `SSN` |
| Credit card | 13–19 digits that pass a **Luhn** check, and a nearby word such as `card`, `Visa`, or `payment` |
| IP | IPv4 (not version-like `3.13.0.1`) and IPv6, including compressed `::` forms |
| Date of birth | Only next to `DOB` / `date of birth` / `born`. Formats: `DD/MM/YYYY`, `YYYY-MM-DD`, `12 March 1994` |
| Person names | List in `data/gazetteer.json`, `Contact Person:` lines, and a few cue words (`from`, `Dear`, `Mr`) |
| Company / trust | Gazetteer plus suffixes such as `Limited`, `Ltd`, `LLP`, `LLC`, `Inc`, `Family Trust` |
| Address | Gazetteer offices, Indian PIN/street patterns, and simple US `Street` + ZIP patterns |

CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names are **not** treated as PII.

Fake values are hashed from the original so they stay stable. Emails use `example.com`. IPs use documentation ranges (`192.0.2.x`, `2001:db8::`). SSNs use invalid area/group numbers (`000-00-xxxx`).

## Known limitations

- A person who is not in the gazetteer and has no cue (`Contact Person:`, `from`, `Mr`) can be missed.
- Generic Title Case matching is **not** used on the whole prospectus, because headings like “Fresh Issue” and “Equity Shares” would be tagged as names.
- IPv4 values where every octet is small (for example `8.8.8.8`) may be skipped so software versions like `3.13.0.1` are not redacted.
- Bare 10-digit numbers with no `+` country code are not phones (avoids ticket IDs).
- Address spans can run a little long or short versus the labeled gold span.
- Credit cards without a nearby word such as `card` / `Visa` / `payment` are left alone so order numbers are not redacted.
- These are precision-first choices. Misses (false negatives) are possible; extra redactions (false positives) should stay rare on structured types.

## How evaluation works

Gold labels live in `data/gold_labels.json`.

**Attached-document evaluation** uses prospectus pages **1, 5, 6, 39** only, and only when the file looks like the KSH Red Herring Prospectus (several known phrases on those pages). A random long PDF is not scored. Each labeled span is one occurrence. A prediction is a true positive when it has the **same type on the same page** and the **character offsets overlap** (at least half of the shorter span). The same string twice counts twice — we do not collapse to unique `(text, type)` pairs.

Reported numbers: **precision**, **recall**, **F1**, and **character-level accuracy**. If nothing was scored, the value is **N/A**, not 1.0.

**Synthetic unit tests** are separate snippets (SSN, card, DOB, IP, extra date/phone/IPv6 shapes). They check the detectors. They are **not** added into the prospectus overall score.

False-positive and false-negative examples in the report are **masked** so original PII is not written to disk in logs.

```bash
python main.py samples/Red_Herring_Prospectus.pdf -o output/KSH_RHP_redacted.docx --evaluate
```

Writes:

- `output/KSH_RHP_redacted.docx`
- `evaluation_report.md`
- `output/evaluation_metrics.json`

## How to add a new PII type

1. Add a detector function in `redact/detectors.py` and list it in `DETECTORS`.
2. Add a fake generator branch in `redact/replacements.py`.
3. Add gold examples in `data/gold_labels.json` (prospectus page and/or a synthetic snippet).
4. Re-run `python main.py samples/Red_Herring_Prospectus.pdf --evaluate`.

## Layout

- `redact/` — extract, detect, replace, write, evaluate
- `data/gazetteer.json` — names, companies, addresses for this prospectus
- `data/gold_labels.json` — labels for pages 1, 5, 6, 39 and synthetic tests
- `app.py` — upload UI (Railway / Vercel)
- `Dockerfile`, `railway.toml`, `Procfile` — Railway
- `vercel.json`, `pyproject.toml` — Vercel
