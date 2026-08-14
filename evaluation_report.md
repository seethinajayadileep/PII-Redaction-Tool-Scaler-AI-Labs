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

- **Precision:** 0.769  (TP=70, FP=21)
- **Recall:** 0.972  (TP=70, FN=2)
- **F1:** 0.859
- **Accuracy (character-level, mean over scored pages):** 0.961
- **Scored:** true

### By PII type (attached document)

| Type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| address | 0.286 | 1.000 | 0.444 | 2 | 5 | 0 |
| company | 0.811 | 0.938 | 0.870 | 30 | 7 | 2 |
| email | 0.600 | 1.000 | 0.750 | 6 | 4 | 0 |
| name | 0.935 | 1.000 | 0.967 | 29 | 2 | 0 |
| phone | 0.500 | 1.000 | 0.667 | 3 | 3 | 0 |

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
- Scoring requires a prospectus fingerprint (known phrases in the file).
  Word files are matched to gold pages by content. Any other file is N/A.
- These document scores are for the labeled sample, not the full prospectus.

## False positives / false negatives

Examples are masked so original PII is not written into the report.

Masked false positives (predicted, not in gold):
- page 1: **** T**** ** M******* B******* C****** O** P***** F***** B***** P*** * 4** **** M*********** I**** (address)
- page 1: ***** **** a** ***** V****** B********* C***** T***** * K**** P*** * 4** **** M*********** I**** (address)
- page 1: ****** E****** **** 1** F***** * * * M**** V******* (****** M***** ******* (************* I**** (address)
- page 1: F******* L*** I***** I**** P****** L****** (company)
- page 1: B******* M**** E******** P****** L****** (company)
- page 1: B******* M**** E******** P****** L****** (company)
- page 1: ***@***.*** (email)
- page 1: ***@***.*** (email)
- page 1: K** I************ P****** L****** (company)
- page 1: M*** I***** I**** P****** L****** (company)
- page 1: S***** G************ (name)
- page 1: * ** ** **** **** (phone)
- page 1: +** ***** ***** (phone)
- page 5: ****** E****** **** 1** F***** * * * M**** V******* (****** M***** ******* (************* I**** (address)
- page 5: F******* L*** I***** I**** P****** L****** (company)

Masked false negatives (gold, missed):
- page 1: E****** F***** T**** (company)
- page 5: E****** F***** T**** (company)

