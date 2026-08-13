"""End-to-end redaction: PDF or plain text → redacted pages + stats."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from redact.apply import ReplacementTable, apply_redactions
from redact.detectors import detect_all
from redact.extract import clean_text_file, extract_pages
from redact.writer import write_docx

def _merge_counts(*count_dicts: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in count_dicts:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + value
    return merged

@dataclass
class RedactionResult:
    pages: list[str]
    original_pages: list[str]
    mapping: dict[str, str]
    counts: dict[str, int]
    docx_path: Path | None = None
    extra: dict = field(default_factory=dict)

def redact_pages(original_pages: list[str]) -> RedactionResult:
    """Redact a list of already-extracted page strings."""
    table = ReplacementTable()
    redacted_pages: list[str] = []
    all_counts: dict[str, int] = {}
    for page in original_pages:
        spans = detect_all(page)
        new_page, page_counts, table = apply_redactions(page, spans, table)
        redacted_pages.append(new_page)
        all_counts = _merge_counts(all_counts, page_counts)
    return RedactionResult(pages=redacted_pages, original_pages=original_pages, mapping=table.mapping, counts=all_counts)

def redact_document(source: str | Path, output_docx: str | Path | None=None) -> RedactionResult:
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix == '.pdf':
        original_pages = extract_pages(source)
    else:
        original_pages = [clean_text_file(source.read_text(encoding='utf-8', errors='replace'))]
    result = redact_pages(original_pages)
    if output_docx:
        result.docx_path = write_docx(result.pages, output_docx, source_name=source.name, counts=result.counts)
    return result