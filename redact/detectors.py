"""Find PII spans in text.

Each detector returns a list of dicts:
    {"start": int, "end": int, "text": str, "type": str}

This is regex + a small gazetteer, not a neural NER model.
"""
from __future__ import annotations
import ipaddress
import json
import re
from functools import lru_cache
from pathlib import Path
GAZETTEER_PATH = Path(__file__).resolve().parent.parent / 'data' / 'gazetteer.json'
PII_TYPES = ('name', 'email', 'phone', 'company', 'address', 'ssn', 'credit_card', 'dob', 'ip')
EMAIL_RE = re.compile('\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b')
PHONE_RE = re.compile('\n    (?<!\\d)\n    (?:\n        \\+\\s?\\d{1,3}(?:[\\s\\-.()]?\\d){7,14}     # +91 98765..., +1 415 555 2671\n        |\n        \\+?\\s?1[\\s\\-.]?\\(?\\d{3}\\)?[\\s.\\-]?\\d{3}[\\s.\\-]?\\d{4}  # +1 (415) 555-2671\n        |\n        \\(\\d{3}\\)[\\s.\\-]?\\d{3}[\\s.\\-]?\\d{4}    # (415) 555-2671\n        |\n        \\b\\d{3}[\\s.\\-]\\d{3}[\\s.\\-]\\d{4}\\b      # 415-555-2671\n    )\n    (?!\\d)\n    ', re.VERBOSE)
SSN_DASH_RE = re.compile('\\b\\d{3}-\\d{2}-\\d{4}\\b')
SSN_CONTEXT_RE = re.compile('(?:SSN|social\\s+security(?:\\s+number)?)\\s*[:#]?\\s*(\\d{3}-?\\d{2}-?\\d{4})', re.IGNORECASE)
CARD_RE = re.compile('\\b(?:\\d[ -]?){13,19}\\b')
CARD_LEAD_RE = re.compile('\\b(?:visa|mastercard|amex|american\\s+express|payment\\s+card(?:\\s+number)?|credit\\s+card(?:\\s+number)?|debit\\s+card(?:\\s+number)?|card(?:\\s+number)?)\\s*[:#]?\\s*$', re.IGNORECASE)
IPV4_RE = re.compile('(?<![\\w.])(?:(?:25[0-5]|2[0-4]\\d|[01]?\\d{1,2})\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d{1,2})(?![\\w])')
IPV6_RE = re.compile('(?<![A-Za-z0-9:])(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}(?![A-Za-z0-9:])|(?<![A-Za-z0-9:])(?:[A-Fa-f0-9]{1,4}:){1,7}:(?:[A-Fa-f0-9]{1,4})?(?![A-Za-z0-9:])|(?<![A-Za-z0-9:])(?:[A-Fa-f0-9]{1,4}:){1,6}(?::[A-Fa-f0-9]{1,4}){1,6}(?![A-Za-z0-9:])|(?<![A-Za-z0-9:])::(?:[A-Fa-f0-9]{1,4}:){0,6}[A-Fa-f0-9]{1,4}(?![A-Za-z0-9:])')
MONTH = '(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
DOB_LABEL = '(?:date\\s+of\\s+birth|d\\.?o\\.?b\\.?|born(?:\\s+on)?)'
DOB_RE = re.compile(DOB_LABEL + '\\s*[:\\-]?\\s*' + '(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\d{4}-\\d{2}-\\d{2}|\\d{1,2}\\s+' + MONTH + '\\s+\\d{4}|' + MONTH + '\\s+\\d{1,2},?\\s+\\d{4})', re.IGNORECASE)
COMPANY_SUFFIX_RE = re.compile("\\b(?:[A-Z][A-Za-z0-9&.'’\\-]+(?:[ \\t]+[A-Z0-9][A-Za-z0-9&.'’\\-]*){0,8})(?:[ \\t]+(?:Private|Pvt\\.?))?[ \\t]+(?:Limited|Ltd\\.?|LLP|LLC|PLC|Corporation|Corp\\.?|Inc\\.?|GmbH|Pte\\.?[ \\t]+Ltd\\.?)\\b")
FAMILY_TRUST_RE = re.compile('\\b[A-Z][A-Za-z]+[ \\t]+Family[ \\t]+Trust\\b', re.IGNORECASE)
CONTACT_PERSON_RE = re.compile('Contact\\s+Person:\\s*([A-Z][A-Za-z.]+(?:[ \\t]+[A-Z][A-Za-z.]+){0,3}(?:[ \\t]*/[ \\t]*[A-Z][A-Za-z.]+(?:[ \\t]+[A-Z][A-Za-z.]+){0,3})?)')
NAME_CONTEXT_RE = re.compile("\\b(?i:from|dear|signed(?:\\s+by)?|regards|applicant|passenger|requester|customer|user|employee|reported\\s+by)\\s*:?\\s+([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,3})")
NAME_TITLE_RE = re.compile("\\b(?:Mr|Mrs|Ms|Dr|Prof)\\.?\\s+([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\\s+[A-Z][a-z]+){0,3})")
US_ADDRESS_RE = re.compile("\\b\\d{1,5}\\s+[A-Z][A-Za-z0-9 .'-]+?(?:Street|St\\.|Avenue|Ave\\.|Road|Rd\\.|Lane|Ln\\.|Drive|Dr\\.|Boulevard|Blvd\\.|Way|Court|Ct\\.)(?:,?\\s+[A-Z][A-Za-z .]+)?(?:,?\\s+[A-Z]{2}\\s+\\d{5}(?:-\\d{4})?)?", re.IGNORECASE)
COMPANY_DENY = {'companies act', 'limited liability', 'the company', 'our company', 'public limited company', 'private limited company', 'equity shares of face value'}
COMPANY_STOPWORDS = {'offer', 'prospectus', 'act', 'regulation', 'regulations', 'section', 'dated', 'page', 'equity', 'share', 'shares', 'issue', 'fresh', 'board', 'built'}
NAME_DENY = {'red herring', 'offer price', 'fresh issue', 'equity shares', 'book built', 'contact person', 'company secretary', 'compliance officer', 'registered office', 'corporate office', 'managing director', 'executive director', 'independent director', 'statutory auditors', 'lead managers', 'care report', 'fiscal year', 'india limited'}

@lru_cache(maxsize=1)
def load_gazetteer() -> dict:
    with GAZETTEER_PATH.open(encoding='utf-8') as fh:
        return json.load(fh)

def _span(start: int, end: int, text: str, pii_type: str) -> dict:
    return {'start': start, 'end': end, 'text': text[start:end], 'type': pii_type}

def _find_literal(text: str, needle: str, pii_type: str) -> list[dict]:
    if not needle.strip():
        return []
    spans = []
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    for match in pattern.finditer(text):
        spans.append(_span(match.start(), match.end(), text, pii_type))
    return spans

def detect_emails(text: str) -> list[dict]:
    return [_span(m.start(), m.end(), text, 'email') for m in EMAIL_RE.finditer(text)]

def detect_phones(text: str) -> list[dict]:
    spans = []
    for match in PHONE_RE.finditer(text):
        raw = match.group(0).strip()
        start = match.start()
        end = start + len(raw)
        if start > 0 and text[start - 1].isdigit():
            continue
        if end < len(text) and text[end].isdigit():
            continue
        digits = re.sub('\\D', '', raw)
        if len(digits) < 10 or len(digits) > 15:
            continue
        spans.append(_span(start, end, text, 'phone'))
    return spans

def detect_ssn(text: str) -> list[dict]:
    spans = []
    for match in SSN_DASH_RE.finditer(text):
        spans.append(_span(match.start(), match.end(), text, 'ssn'))
    for match in SSN_CONTEXT_RE.finditer(text):
        spans.append(_span(match.start(1), match.end(1), text, 'ssn'))
    return spans

def _luhn_ok(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

def detect_credit_cards(text: str) -> list[dict]:
    spans = []
    for match in CARD_RE.finditer(text):
        raw = match.group(0).strip()
        digits = re.sub('\\D', '', raw)
        if not _luhn_ok(digits):
            continue
        lead = text[:match.start()]
        if not CARD_LEAD_RE.search(lead):
            continue
        spans.append(_span(match.start(), match.start() + len(raw), text, 'credit_card'))
    return spans

def _ipv4_looks_like_version(value: str) -> bool:
    parts = [int(p) for p in value.split('.')]
    return parts[0] < 10 and max(parts) < 20

def detect_ips(text: str) -> list[dict]:
    spans = []
    for match in IPV4_RE.finditer(text):
        value = match.group(0)
        if _ipv4_looks_like_version(value):
            continue
        try:
            ipaddress.IPv4Address(value)
        except ValueError:
            continue
        spans.append(_span(match.start(), match.end(), text, 'ip'))
    for match in IPV6_RE.finditer(text):
        value = match.group(0)
        try:
            ipaddress.IPv6Address(value)
        except ValueError:
            continue
        spans.append(_span(match.start(), match.end(), text, 'ip'))
    return spans

def detect_dobs(text: str) -> list[dict]:
    spans = []
    for match in DOB_RE.finditer(text):
        spans.append(_span(match.start(1), match.end(1), text, 'dob'))
    return spans

def detect_names(text: str) -> list[dict]:
    gaz = load_gazetteer()
    people = sorted(gaz['people'], key=len, reverse=True)
    spans: list[dict] = []
    for name in people:
        if name.lower() in NAME_DENY:
            continue
        spans.extend(_find_literal(text, name, 'name'))
    for regex in (CONTACT_PERSON_RE, NAME_CONTEXT_RE, NAME_TITLE_RE):
        for match in regex.finditer(text):
            value = match.group(1)
            for part in re.split('\\s*/\\s*', value):
                part = part.strip()
                if len(part.split()) < 2 and regex is not NAME_TITLE_RE:
                    continue
                if part.lower() in NAME_DENY:
                    continue
                start = text.find(part, match.start(1), match.end(1))
                if start >= 0:
                    spans.append(_span(start, start + len(part), text, 'name'))
    return spans

def detect_companies(text: str) -> list[dict]:
    gaz = load_gazetteer()
    companies = sorted(gaz['companies'], key=len, reverse=True)
    spans: list[dict] = []
    for name in companies:
        if name.lower() in COMPANY_DENY:
            continue
        spans.extend(_find_literal(text, name, 'company'))
    for regex in (COMPANY_SUFFIX_RE, FAMILY_TRUST_RE):
        for match in regex.finditer(text):
            value = match.group(0).strip()
            lowered = value.lower()
            if lowered in COMPANY_DENY:
                continue
            tokens = set(re.findall('[a-z]+', lowered))
            if tokens & COMPANY_STOPWORDS:
                continue
            if lowered.startswith('the ') and 'limited' not in lowered:
                continue
            spans.append(_span(match.start(), match.end(), text, 'company'))
    return spans

def detect_addresses(text: str) -> list[dict]:
    gaz = load_gazetteer()
    addresses = sorted(gaz['addresses'], key=len, reverse=True)
    spans: list[dict] = []
    for addr in addresses:
        compact = ' '.join(addr.split())
        spans.extend(_find_literal(text, compact, 'address'))
        spans.extend(_find_literal(text, compact.replace('–', '-'), 'address'))
        spans.extend(_find_literal(text, compact.replace('-', '–'), 'address'))
    pin_re = re.compile('(?:Plot\\s+No\\.?|Village|Tower|Wing|Floor|House|Marg|Road|Complex|\\d{1,4}/\\d{1,4})[\\w ,./–\\-()]{10,160}?(?:Maharashtra|Mumbai|Pune|India)(?:,?\\s*India)?(?:,?\\s*\\d{3}\\s?\\d{3})?', re.IGNORECASE)
    for match in pin_re.finditer(text):
        if len(match.group(0).strip()) < 20:
            continue
        spans.append(_span(match.start(), match.end(), text, 'address'))
    street_re = re.compile('\\b\\d{1,5}\\s+[A-Za-z][A-Za-z .]{1,40}(?:Road|Marg|Street|Nagar|Lane)[\\w ,./–\\-()]{0,80}?\\d{3}\\s?\\d{3}(?:,?\\s*Maharashtra)?(?:,?\\s*India)?', re.IGNORECASE)
    for match in street_re.finditer(text):
        if len(match.group(0).strip()) < 16:
            continue
        spans.append(_span(match.start(), match.end(), text, 'address'))
    for match in US_ADDRESS_RE.finditer(text):
        if len(match.group(0).strip()) < 12:
            continue
        spans.append(_span(match.start(), match.end(), text, 'address'))
    return spans
DETECTORS = (detect_emails, detect_phones, detect_ssn, detect_credit_cards, detect_ips, detect_dobs, detect_names, detect_companies, detect_addresses)

def detect_all(text: str) -> list[dict]:
    """Run every detector and return unsorted, possibly overlapping spans."""
    spans: list[dict] = []
    for detector in DETECTORS:
        spans.extend(detector(text))
    return spans