"""OCR helpers for identity-document images inside a Word file."""

from __future__ import annotations

import io
import re

PAN_COMPACT_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
ID_MARKERS = (
    "permanent account",
    "income tax",
    "aadhaar",
    "aadhar",
    "uidai",
    "passport no",
    "passport number",
    "date of birth",
    "d.o.b",
    "d.o.b.",
    "govt of india",
    "govt. of india",
    "government of india",
    "driving licence",
    "driving license",
    "voter id",
    "election commission",
    "unique identification",
)
ID_CONTEXT = (
    "father",
    "address",
    "male",
    "female",
    "signature",
    "uttar pradesh",
    "maharashtra",
    "karnataka",
    "gujarat",
    "rajasthan",
    "west bengal",
    "tamil nadu",
)


class OcrUnavailableError(RuntimeError):
    """Raised when images must be scanned but Tesseract is missing."""


def ocr_is_available() -> bool:
    try:
        import pytesseract
        from PIL import Image  # noqa: F401

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def require_ocr() -> None:
    if not ocr_is_available():
        raise OcrUnavailableError(
            "OCR is required to redact identity-document images in Word files. "
            "Install Tesseract OCR and the Python packages Pillow and pytesseract."
        )


def ocr_image_bytes(data: bytes) -> str:
    require_ocr()
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    try:
        return pytesseract.image_to_string(image) or ""
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "Tesseract OCR is not installed or not on PATH."
        ) from exc


def image_is_sensitive(ocr_text: str) -> bool:
    """True for PAN cards and similar ID scans, not ordinary logos."""
    if not ocr_text.strip():
        return False
    compact = re.sub(r"\s+", "", ocr_text.upper())
    if PAN_COMPACT_RE.search(compact):
        return True
    lowered = ocr_text.lower()
    if any(marker in lowered for marker in ID_MARKERS):
        return True
    context_hits = sum(1 for token in ID_CONTEXT if token in lowered)
    if context_hits >= 2:
        return True
    from redact.detectors import detect_addresses, detect_dobs, detect_emails, detect_phones

    if detect_emails(ocr_text) or detect_phones(ocr_text) or detect_dobs(ocr_text):
        return True
    if detect_addresses(ocr_text) and context_hits >= 1:
        return True
    return False


def placeholder_image(fmt: str = "PNG") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (640, 360), (236, 236, 236))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 627, 347), outline=(90, 90, 90), width=4)
    text = "SENSITIVE IMAGE REMOVED"
    font = ImageFont.load_default()
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ):
        try:
            font = ImageFont.truetype(path, 28)
            break
        except OSError:
            continue
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (640 - (bbox[2] - bbox[0])) // 2
    y = (360 - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, fill=(40, 40, 40), font=font)
    buffer = io.BytesIO()
    kind = "JPEG" if fmt.upper() in {"JPG", "JPEG"} else "PNG"
    image.save(buffer, format=kind, optimize=True, quality=85)
    return buffer.getvalue()
