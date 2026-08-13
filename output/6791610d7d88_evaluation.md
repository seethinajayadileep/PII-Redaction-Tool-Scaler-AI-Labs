# PII redaction evaluation report

Gold labels were written by hand for a sample of prospectus pages, plus a
synthetic ticket-log snippet that covers SSN, credit card, DOB, and IP
(those types do not appear in the RHP).

## Overall

- **Precision:** 1.000  (TP=81, FP=0)
- **Recall:** 1.000  (TP=81, FN=0)
- **Accuracy (token-level, mean over scored pages):** 0.989

## By PII type

| Type | Precision | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| address | 1.000 | 1.000 | 8 | 0 | 0 |
| company | 1.000 | 1.000 | 30 | 0 | 0 |
| credit_card | 1.000 | 1.000 | 1 | 0 | 0 |
| dob | 1.000 | 1.000 | 1 | 0 | 0 |
| email | 1.000 | 1.000 | 9 | 0 | 0 |
| ip | 1.000 | 1.000 | 1 | 0 | 0 |
| name | 1.000 | 1.000 | 24 | 0 | 0 |
| phone | 1.000 | 1.000 | 6 | 0 | 0 |
| ssn | 1.000 | 1.000 | 1 | 0 | 0 |

## Method

- Gold set: prospectus pages **1, 5, 6, 39** (cover, issuer page, BRLM contacts, summary)
  plus one synthetic ticket-log line for SSN / card / DOB / IP.
- A predicted span matches gold when type agrees and normalised text is identical
  (or one text contains the other, minimum 10 characters — used for addresses).
- Token-level accuracy: each whitespace token on those pages is PII or not;
  accuracy = (TP + TN) / all tokens, then averaged across scored pages.
- CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names
  were **not** labeled as PII.
- `CARE Report` was not labeled as a company (it is a document title).
- These scores are for the labeled sample, not the full 130-page PDF.

## Notes

