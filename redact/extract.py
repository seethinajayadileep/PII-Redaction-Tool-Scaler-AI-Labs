"""Extract text from a PDF and clean a plain-text file."""
from __future__ import annotations
import re
from pathlib import Path
from pypdf import PdfReader

def extract_pages(pdf_path: str | Path) -> list[str]:
    """Return one cleaned text string per PDF page."""
    reader = PdfReader(str(pdf_path))
    return [clean_page_text(page.extract_text() or '') for page in reader.pages]

def clean_text_file(text: str) -> str:
    """Keep line breaks in .txt files; only normalise Windows newlines."""
    if not text:
        return ''
    return text.replace('\r\n', '\n').replace('\r', '\n')

def clean_page_text(text: str) -> str:
    """Rebuild PDF text: join broken words, keep paragraph gaps.

    Some PDFs split a word across lines (``REGIST\\nERED`` or
    ``kshinternational.co\\nm``). Those letter-to-letter newlines are joined.
    A single newline between words becomes a space. Blank lines stay as
    paragraph breaks so the Word file is readable.
    """
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub('\\n{3,}', '\n\n', text)
    for _ in range(30):
        nxt = re.sub('([A-Za-z0-9])\\n([A-Za-z0-9])', '\\1\\2', text)
        if nxt == text:
            break
        text = nxt
    text = re.sub('(?<!\\n)\\n(?!\\n)', ' ', text)
    text = re.sub('[ \\t]+', ' ', text)
    text = re.sub(' *\\n *', '\n', text)
    text = text.replace('. com', '.com').replace('. in', '.in')
    text = text.replace('. org', '.org').replace('. co ', '.co ')
    return text.strip()