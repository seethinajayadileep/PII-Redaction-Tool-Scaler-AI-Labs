# PII redaction evaluation report

Gold labels were written by hand for a sample of prospectus pages, plus a
synthetic ticket-log snippet that covers SSN, credit card, DOB, and IP
(those types do not appear in the RHP).

## Overall

- **Precision:** 0.500  (TP=11, FP=11)
- **Recall:** 0.379  (TP=11, FN=18)
- **Accuracy (token-level, mean over scored pages):** 0.641

## By PII type

| Type | Precision | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| address | 0.500 | 0.333 | 1 | 1 | 2 |
| company | 0.500 | 0.111 | 1 | 1 | 8 |
| credit_card | 0.500 | 1.000 | 1 | 1 | 0 |
| dob | 0.500 | 1.000 | 1 | 1 | 0 |
| email | 0.500 | 0.667 | 2 | 2 | 1 |
| ip | 0.500 | 1.000 | 1 | 1 | 0 |
| name | 0.500 | 0.250 | 2 | 2 | 6 |
| phone | 0.500 | 0.500 | 1 | 1 | 1 |
| ssn | 0.500 | 1.000 | 1 | 1 | 0 |

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

Example false positives (predicted, not in gold):
- `+91 9876543210` (phone)
- `10.0.5.22` (ip)
- `12/03/1994` (dob)
- `14 mg road, pune – 411 001, maharashtra, india` (address)
- `219-09-9999` (ssn)
- `4111-1111-1111-1111` (credit_card)
- `helix tickets pvt ltd.` (company)
- `rashhi.patil@gmail.com` (email)
- `rashi patil` (name)
- `rohan dey` (name)
- `rohan.dey@gmail.com` (email)

Example false negatives (gold, missed):
- `+ 91 20 45053237` (phone)
- `11/3, 11/4 and 11/5 village birdewadi chakan taluka - khed pune – 410 501 maharashtra, india` (address)
- `201, tower 2, montreal business centre, off pallod farms, baner pune – 411 045 maharashtra, india` (address)
- `annapurna family trust` (company)
- `broad family trust` (company)
- `cs.connect@kshinternational.com` (email)
- `dhaulagiri family trust` (company)
- `everest family trust` (company)
- `kanchenjunga family trust` (company)
- `ksh international limited` (company)
- `kushal subbayya hegde` (name)
- `makalu family trust` (company)
- `pushpa kushal hegde` (name)
- `rajesh kushal hegde` (name)
- `rakhi girija shetty` (name)

