"""Score detections against a hand-labeled gold set.

Each gold/predicted span is one occurrence (page + character offsets).
The same string on the same page twice counts twice.

Attached-document scores use prospectus pages 1, 5, 6, 39 only.
Synthetic ticket snippets are scored in a separate section and are not
folded into the PDF totals.

If nothing was scored, precision/recall/F1/accuracy are None (shown as N/A).
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from pathlib import Path
from redact.apply import resolve_overlaps
from redact.detectors import detect_all
ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / 'data' / 'gold_labels.json'

def _norm(text: str) -> str:
    return re.sub('\\s+', ' ', text).strip().lower()

def load_gold(path: Path=GOLD_PATH) -> dict:
    with path.open(encoding='utf-8') as fh:
        return json.load(fh)

def mask_value(text: str) -> str:
    """Hide original PII in reports. Keep shape, not the real string."""
    pieces = []
    for token in re.findall('\\S+', text):
        if '@' in token:
            pieces.append('***@***.***')
        elif re.search('\\d', token) and len(token) >= 4:
            pieces.append('*' * min(len(token), 10))
        elif len(token) <= 2:
            pieces.append('*' * len(token))
        else:
            pieces.append(token[0] + '*' * (len(token) - 1))
    return ' '.join(pieces)

def _ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den

def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)

def locate_gold(text: str, gold_items: list[dict]) -> list[dict]:
    """Turn gold labels into occurrence spans with character offsets.

    Each labeled string is located every time it appears on the page, so two
    copies of the same name count as two gold occurrences.
    """
    used: list[tuple[int, int]] = []
    spans: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in gold_items:
        if 'start' in item and 'end' in item:
            start, end = (int(item['start']), int(item['end']))
            spans.append({'start': start, 'end': end, 'text': text[start:end], 'type': item['type']})
            used.append((start, end))
            continue
        key = (_norm(item['text']), item['type'])
        if key in seen:
            continue
        seen.add(key)
        pattern = re.compile(re.escape(item['text']).replace('\\ ', '\\s+'), re.IGNORECASE)
        for match in pattern.finditer(text):
            start, end = (match.start(), match.end())
            if any((start < u_end and u_start < end for u_start, u_end in used)):
                continue
            used.append((start, end))
            spans.append({'start': start, 'end': end, 'text': text[start:end], 'type': item['type']})
    return spans

def _overlap_len(a: dict, b: dict) -> int:
    return max(0, min(a['end'], b['end']) - max(a['start'], b['start']))

def _same_occurrence(pred: dict, gold: dict) -> bool:
    if pred['type'] != gold['type']:
        return False
    overlap = _overlap_len(pred, gold)
    if overlap <= 0:
        return False
    shortest = min(pred['end'] - pred['start'], gold['end'] - gold['start'])
    return overlap >= max(1, int(0.5 * shortest))

def _align(pred: list[dict], gold: list[dict]):
    """Greedy 1-1 match of predicted occurrences to gold occurrences."""
    unmatched = list(gold)
    tp = []
    fp = []
    for item in sorted(pred, key=lambda s: -(s['end'] - s['start'])):
        hit = next((g for g in unmatched if _same_occurrence(item, g)), None)
        if hit is not None:
            tp.append(item)
            unmatched.remove(hit)
        else:
            fp.append(item)
    return (tp, fp, unmatched)

def _token_flags_from_spans(text: str, spans: list[dict]) -> list[bool]:
    flags = [False] * len(text)
    for span in spans:
        for i in range(max(0, span['start']), min(len(text), span['end'])):
            flags[i] = True
    return flags

def _summarize(tp: int, fp: int, fn: int, accuracy: float | None, by_type: dict) -> dict:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': _f1(precision, recall), 'accuracy': accuracy, 'by_type': by_type}

def _by_type_stats(tp: list[dict], fp: list[dict], fn: list[dict]) -> dict:
    types = {s['type'] for s in tp + fp + fn}
    out = {}
    for pii_type in sorted(types):
        tps = sum((1 for s in tp if s['type'] == pii_type))
        fps = sum((1 for s in fp if s['type'] == pii_type))
        fns = sum((1 for s in fn if s['type'] == pii_type))
        precision = _ratio(tps, tps + fps)
        recall = _ratio(tps, tps + fns)
        out[pii_type] = {'tp': tps, 'fp': fps, 'fn': fns, 'precision': precision, 'recall': recall, 'f1': _f1(precision, recall)}
    return out

def score_text(text: str, gold_items: list[dict], *, page: int | None=None) -> dict:
    gold = locate_gold(text, gold_items)
    pred = resolve_overlaps(detect_all(text))
    tp, fp, fn = _align(pred, gold)
    gold_flags = _token_flags_from_spans(text, gold)
    pred_flags = _token_flags_from_spans(text, pred)
    token_tp = token_fp = token_fn = token_tn = 0
    for g, p in zip(gold_flags, pred_flags):
        if g and p:
            token_tp += 1
        elif p and (not g):
            token_fp += 1
        elif g and (not p):
            token_fn += 1
        else:
            token_tn += 1
    total = token_tp + token_fp + token_fn + token_tn
    accuracy = _ratio(token_tp + token_tn, total)
    result = _summarize(len(tp), len(fp), len(fn), accuracy, _by_type_stats(tp, fp, fn))
    result['false_positives'] = [{'type': s['type'], 'example': mask_value(s['text']), 'start': s['start'], 'end': s['end']} for s in fp[:15]]
    result['false_negatives'] = [{'type': s['type'], 'example': mask_value(s['text']), 'start': s['start'], 'end': s['end']} for s in fn[:15]]
    if page is not None:
        result['page'] = page
    return result

def is_labeled_prospectus(pages: list[str]) -> bool:
    """True only for the KSH RHP sample, not every long PDF."""
    if len(pages) < 39:
        return False
    blob = '\n'.join((pages[i] for i in (0, 4, 5, 38) if i < len(pages))).lower()
    phrases = ('red herring prospectus', 'ksh international limited', 'book built offer', 'nuvama wealth management')
    return sum((1 for phrase in phrases if phrase in blob)) >= 3

def evaluate_pages(original_pages: list[str], gold: dict | None=None) -> dict:
    gold = gold or load_gold()
    per_page = []
    totals = defaultdict(int)
    type_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    gold_pages = gold.get('pages') or []
    score_prospectus = is_labeled_prospectus(original_pages)
    if score_prospectus:
        for spec in gold_pages:
            page_no = spec['page']
            if page_no < 1 or page_no > len(original_pages):
                continue
            result = score_text(original_pages[page_no - 1], spec['spans'], page=page_no)
            per_page.append(result)
            for key in ('tp', 'fp', 'fn'):
                totals[key] += result[key]
            for pii_type, stats in result['by_type'].items():
                for key in ('tp', 'fp', 'fn'):
                    type_totals[pii_type][key] += stats[key]
    by_type = {}
    for pii_type, stats in sorted(type_totals.items()):
        tps, fps, fns = (stats['tp'], stats['fp'], stats['fn'])
        precision = _ratio(tps, tps + fps)
        recall = _ratio(tps, tps + fns)
        by_type[pii_type] = {'tp': tps, 'fp': fps, 'fn': fns, 'precision': precision, 'recall': recall, 'f1': _f1(precision, recall)}
    acc_values = [p['accuracy'] for p in per_page if p['accuracy'] is not None]
    accuracy = sum(acc_values) / len(acc_values) if acc_values else None
    document = _summarize(totals['tp'], totals['fp'], totals['fn'], accuracy, by_type)
    document['pages'] = per_page
    document['scored'] = bool(per_page)
    synthetic_items = []
    syn_totals = defaultdict(int)
    syn_types: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in gold.get('synthetic', []):
        result = score_text(item['text'], item['spans'])
        result['name'] = item.get('name', 'synthetic')
        synthetic_items.append(result)
        for key in ('tp', 'fp', 'fn'):
            syn_totals[key] += result[key]
        for pii_type, stats in result['by_type'].items():
            for key in ('tp', 'fp', 'fn'):
                syn_types[pii_type][key] += stats[key]
    syn_by_type = {}
    for pii_type, stats in sorted(syn_types.items()):
        tps, fps, fns = (stats['tp'], stats['fp'], stats['fn'])
        precision = _ratio(tps, tps + fps)
        recall = _ratio(tps, tps + fns)
        syn_by_type[pii_type] = {'tp': tps, 'fp': fps, 'fn': fns, 'precision': precision, 'recall': recall, 'f1': _f1(precision, recall)}
    syn_acc = [s['accuracy'] for s in synthetic_items if s['accuracy'] is not None]
    synthetic = _summarize(syn_totals['tp'], syn_totals['fp'], syn_totals['fn'], sum(syn_acc) / len(syn_acc) if syn_acc else None, syn_by_type)
    synthetic['items'] = synthetic_items
    synthetic['scored'] = bool(synthetic_items)
    return {'precision': document['precision'], 'recall': document['recall'], 'f1': document['f1'], 'accuracy': document['accuracy'], 'tp': document['tp'], 'fp': document['fp'], 'fn': document['fn'], 'by_type': document['by_type'], 'pages': per_page, 'scored': document['scored'], 'synthetic': synthetic}

def _fmt(value: float | None) -> str:
    return 'N/A' if value is None else f'{value:.3f}'

def render_report(metrics: dict) -> str:
    lines = ['# PII redaction evaluation report', '', 'Two scorecards are kept apart:', '', '1. **Attached document** — hand labels on prospectus pages 1, 5, 6, 39.', '2. **Synthetic unit tests** — a small ticket-log snippet (SSN, card, DOB, IP,', '   extra date/phone/IPv6 shapes). These numbers are **not** mixed into (1).', '', 'A predicted span is a true positive when it has the same type as a gold span', 'on the same page and the character offsets overlap by at least half of the', 'shorter span. Each occurrence counts once (not unique text).', '', 'If a denominator is zero, the metric is **N/A** (not 1.0).', '', '## Attached document (prospectus sample pages)', '']
    if not metrics.get('scored'):
        lines.append('No prospectus pages were scored (the file is not the labeled RHP sample).')
        lines.append('')
        lines.append(f'- **Precision:** {_fmt(None)}')
        lines.append(f'- **Recall:** {_fmt(None)}')
        lines.append(f'- **F1:** {_fmt(None)}')
        lines.append(f'- **Accuracy:** {_fmt(None)}')
        lines.append('- **Scored:** false')
        lines.append('')
    else:
        lines.append(f"- **Precision:** {_fmt(metrics['precision'])}  (TP={metrics['tp']}, FP={metrics['fp']})")
        lines.append(f"- **Recall:** {_fmt(metrics['recall'])}  (TP={metrics['tp']}, FN={metrics['fn']})")
        lines.append(f"- **F1:** {_fmt(metrics['f1'])}")
        lines.append(f"- **Accuracy (character-level, mean over scored pages):** {_fmt(metrics['accuracy'])}")
        lines.append('- **Scored:** true')
        lines += ['', '### By PII type (attached document)', '', '| Type | Precision | Recall | F1 | TP | FP | FN |', '|---|---:|---:|---:|---:|---:|---:|']
        for pii_type, stats in metrics['by_type'].items():
            lines.append(f"| {pii_type} | {_fmt(stats['precision'])} | {_fmt(stats['recall'])} | {_fmt(stats['f1'])} | {stats['tp']} | {stats['fp']} | {stats['fn']} |")
        lines.append('')
    syn = metrics.get('synthetic') or {}
    lines += ['## Synthetic unit tests', '', 'These rows test detector formats. They are not part of the PDF overall score.', '']
    if not syn.get('scored'):
        lines.append('No synthetic fixtures were scored.')
        lines.append('')
    else:
        lines.append(f"- **Precision:** {_fmt(syn['precision'])}  (TP={syn['tp']}, FP={syn['fp']})")
        lines.append(f"- **Recall:** {_fmt(syn['recall'])}  (TP={syn['tp']}, FN={syn['fn']})")
        lines.append(f"- **F1:** {_fmt(syn['f1'])}")
        lines.append(f"- **Accuracy:** {_fmt(syn['accuracy'])}")
        lines += ['', '| Type | Precision | Recall | F1 | TP | FP | FN |', '|---|---:|---:|---:|---:|---:|---:|']
        for pii_type, stats in (syn.get('by_type') or {}).items():
            lines.append(f"| {pii_type} | {_fmt(stats['precision'])} | {_fmt(stats['recall'])} | {_fmt(stats['f1'])} | {stats['tp']} | {stats['fp']} | {stats['fn']} |")
        lines.append('')
    lines += ['## Method', '', '- Gold set: prospectus pages **1, 5, 6, 39** plus synthetic ticket snippets.', '- Matching uses **page number + character offsets**, not unique (text, type) keys.', '- Character-level accuracy: each character is PII or not from gold vs predicted spans.', '- CIN, PAN, DIN, rupee amounts, share counts, page numbers, and statute names', '  were **not** labeled as PII.', '- Scoring the attached document requires a prospectus fingerprint (known phrases', '  on the labeled pages). Any other file, including a long unrelated PDF, is N/A.', '- These document scores are for the labeled sample, not the full 130-page PDF.', '', '## False positives / false negatives', '', 'Examples are masked so original PII is not written into the report.', '']
    fps = []
    fns = []
    for page in metrics.get('pages') or []:
        for item in page.get('false_positives') or []:
            fps.append(f"page {page.get('page')}: {item['example']} ({item['type']})")
        for item in page.get('false_negatives') or []:
            fns.append(f"page {page.get('page')}: {item['example']} ({item['type']})")
    if fps:
        lines.append('Masked false positives (predicted, not in gold):')
        for item in fps[:15]:
            lines.append(f'- {item}')
        lines.append('')
    if fns:
        lines.append('Masked false negatives (gold, missed):')
        for item in fns[:15]:
            lines.append(f'- {item}')
        lines.append('')
    if not fps and (not fns) and metrics.get('scored'):
        lines.append('No false positives or false negatives on the labeled prospectus pages.')
        lines.append('')
    return '\n'.join(lines) + '\n'