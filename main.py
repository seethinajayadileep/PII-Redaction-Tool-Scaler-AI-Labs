"""CLI: redact a PDF or text file and optionally score the run."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from redact.evaluate import evaluate_pages, render_report
from redact.pipeline import redact_document
ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = ROOT / 'samples' / 'Red_Herring_Prospectus.pdf'
DEFAULT_DOCX = ROOT / 'output' / 'KSH_RHP_redacted.docx'
DEFAULT_REPORT = ROOT / 'evaluation_report.md'

def main() -> None:
    parser = argparse.ArgumentParser(description='Redact PII from a prospectus or ticket log.')
    parser.add_argument('source', nargs='?', default=str(DEFAULT_PDF), help='PDF or .txt file')
    parser.add_argument('-o', '--output', default=str(DEFAULT_DOCX), help='Redacted .docx path')
    parser.add_argument('--evaluate', action='store_true', help='Write evaluation_report.md')
    parser.add_argument('--report', default=str(DEFAULT_REPORT), help='Evaluation report path')
    args = parser.parse_args()
    result = redact_document(args.source, args.output)
    print(f'Wrote {result.docx_path}')
    print('Replacement counts by type:', json.dumps(result.counts, indent=2))
    if args.evaluate:
        metrics = evaluate_pages(result.original_pages)
        report = render_report(metrics)
        Path(args.report).write_text(report, encoding='utf-8')
        (ROOT / 'output' / 'evaluation_metrics.json').write_text(json.dumps(metrics, indent=2, default=str), encoding='utf-8')
        print(report)
        print(f'Wrote {args.report}')
if __name__ == '__main__':
    main()