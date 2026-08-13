"""Resolve overlapping spans and substitute fake values."""
from __future__ import annotations
from redact.replacements import fake_for
TYPE_PRIORITY = {'email': 90, 'ssn': 85, 'credit_card': 85, 'ip': 80, 'phone': 75, 'dob': 70, 'address': 60, 'name': 50, 'company': 40}

def resolve_overlaps(spans: list[dict]) -> list[dict]:
    """Keep longer / higher-priority spans; drop overlaps.

    An email must not also be tagged as a name. A full company name must not
    be split into a shorter nested company.
    """
    ranked = sorted(spans, key=lambda s: (-(s['end'] - s['start']), -TYPE_PRIORITY.get(s['type'], 0), s['start']))
    kept: list[dict] = []
    for span in ranked:
        if any((_overlaps(span, other) for other in kept)):
            continue
        kept.append(span)
    return sorted(kept, key=lambda s: s['start'])

def _overlaps(a: dict, b: dict) -> bool:
    return a['start'] < b['end'] and b['start'] < a['end']

class ReplacementTable:
    """One original string → one fake value for the whole document."""

    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self.used: set[str] = set()
        self._canon: dict[str, str] = {}

    def replace(self, original: str, pii_type: str) -> str:
        key = original.strip()
        if not key:
            return original
        canon = key.lower()
        if canon not in self._canon:
            fake = fake_for(key, pii_type, self.used)
            self._canon[canon] = fake
            self.mapping[key] = fake
        fake = self._canon[canon]
        if key.isupper() and any((ch.isalpha() for ch in key)):
            return fake.upper()
        if fake.isupper() and (not key.isupper()):
            return fake.title()
        return fake

def apply_redactions(text: str, spans: list[dict], table: ReplacementTable | None=None) -> tuple[str, dict[str, int], ReplacementTable]:
    """Replace resolved spans. Returns (new_text, counts, table)."""
    table = table or ReplacementTable()
    resolved = resolve_overlaps(spans)
    counts: dict[str, int] = {}
    pieces: list[str] = []
    cursor = 0
    for span in resolved:
        pieces.append(text[cursor:span['start']])
        pieces.append(table.replace(span['text'], span['type']))
        cursor = span['end']
        counts[span['type']] = counts.get(span['type'], 0) + 1
    pieces.append(text[cursor:])
    return (''.join(pieces), counts, table)