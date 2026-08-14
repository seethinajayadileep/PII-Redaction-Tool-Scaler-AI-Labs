"""Small FastAPI app: upload a PDF, TXT, or DOCX; download a redacted .docx."""
from __future__ import annotations
import base64
import os
import tempfile
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from redact.evaluate import evaluate_pages, render_report
from redact.ocr_images import OcrUnavailableError
from redact.pipeline import redact_document
ROOT = Path(__file__).resolve().parent
DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
SAMPLE_TICKET = ROOT / 'samples' / 'ticket_log.txt'
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
JOB_LIMIT = 32
JOBS: dict[str, dict] = {}

def _writable_dir(preferred: Path) -> Path:
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / 'pii-redact' / preferred.name
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
UPLOAD_DIR = _writable_dir(ROOT / 'uploads')
OUTPUT_DIR = _writable_dir(ROOT / 'output')
app = FastAPI(title='PII Redaction Tool')
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.environ.get('CORS_ORIGINS', '*').split(',') if origin.strip()], allow_methods=['*'], allow_headers=['*'])
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

def _store_job(job_id: str, record: dict) -> None:
    JOBS[job_id] = record
    while len(JOBS) > JOB_LIMIT:
        JOBS.pop(next(iter(JOBS)))

def _run_job(source: Path, filename: str) -> dict:
    job_id = uuid.uuid4().hex[:12]
    docx_path = OUTPUT_DIR / f"{job_id}_redacted.docx"
    try:
        result = redact_document(source, docx_path)
    except OcrUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    docx_bytes = docx_path.read_bytes()
    metrics = None
    report_text = None
    report_path = None
    kind = source.suffix.lower().lstrip(".")
    try:
        metrics = evaluate_pages(result.original_pages, source_kind=kind)
        report_text = render_report(metrics)
        report_path = OUTPUT_DIR / f'{job_id}_evaluation.md'
        report_path.write_text(report_text, encoding='utf-8')
    except Exception:
        metrics = None
        report_text = None
        report_path = None
    metrics_out = {'precision': metrics['precision'], 'recall': metrics['recall'], 'f1': metrics['f1'], 'accuracy': metrics['accuracy'], 'scored': metrics['scored']} if metrics else None
    _store_job(job_id, {'docx': str(docx_path), 'docx_bytes': docx_bytes, 'report': str(report_path) if report_path else None, 'report_text': report_text, 'counts': result.counts, 'metrics': metrics_out})
    return {
        "job_id": job_id,
        "filename": filename,
        "counts": result.counts,
        "metrics": metrics_out,
        "images_removed": (result.extra or {}).get("images_removed", 0),
        "docx_b64": base64.b64encode(docx_bytes).decode("ascii"),
        "report_md": report_text,
    }

@app.get('/health')
def health() -> dict:
    from redact.ocr_images import ocr_is_available

    return {"ok": True, "ocr": ocr_is_available()}

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')

@app.post('/redact')
async def redact(file: UploadFile=File(...)) -> dict:
    suffix = Path(file.filename or "upload.pdf").suffix.lower()
    if suffix not in {".pdf", ".txt", ".docx"}:
        raise HTTPException(400, "Please upload a PDF, TXT, or DOCX file.")
    data = await file.read()
    if not data:
        raise HTTPException(400, 'The file is empty.')
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, 'File is too large (max 20 MB).')
    source = UPLOAD_DIR / f'{uuid.uuid4().hex[:12]}{suffix}'
    source.write_bytes(data)
    try:
        return _run_job(source, file.filename or source.name)
    finally:
        source.unlink(missing_ok=True)

@app.post('/redact/sample')
def redact_sample() -> dict:
    if not SAMPLE_TICKET.exists():
        raise HTTPException(404, 'Sample ticket log is missing.')
    return _run_job(SAMPLE_TICKET, SAMPLE_TICKET.name)

@app.get('/download/docx/{job_id}')
def download_docx(job_id: str) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, 'Unknown job.')
    data = job.get('docx_bytes')
    if not data:
        path = Path(job['docx'])
        if not path.exists():
            raise HTTPException(404, 'File missing.')
        data = path.read_bytes()
    return Response(content=data, media_type=DOCX_TYPE, headers={'Content-Disposition': 'attachment; filename="redacted.docx"'})

@app.get('/download/report/{job_id}')
def download_report(job_id: str) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, 'Unknown job.')
    text = job.get('report_text')
    if text is None and job.get('report'):
        path = Path(job['report'])
        if path.exists():
            text = path.read_text(encoding='utf-8')
    if not text:
        raise HTTPException(404, 'No report for this job.')
    return Response(content=text, media_type='text/markdown; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="evaluation_report.md"'})