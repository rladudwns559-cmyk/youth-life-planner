"""Automated daily comparison of recommendable products against their official pages.

What it does: for every product that can reach the recommendation shelf, it renders the official
page already recorded as the product's source (headless Chromium, or pypdf for a PDF), and renews
the record for 7 more days ONLY when all of these hold:
  * the product name is on the page,
  * no sales-ended marker follows the name,
  * the stored base rates appear on the page in table order, close together.
Anything else is left alone, so the record expires on its own date and drops out of the
recommendation. Nothing is ever changed to a new rate here: a changed rate needs a person.

This is weaker than a person reading the page, so every entry says "automated comparison" in its
evidence note and source title. A plain HTTP 200 or a hash is never treated as confirmation.

Usage (repo root):
  python -m tools.auto_recheck --dry-run --report out.json          # compare only, write a report
  python -m tools.auto_recheck                                      # write today's batch + rebuild public JSON
"""
import argparse
import copy
import io
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tools.list_recommendable_products import recommendable

ROOT = Path(__file__).resolve().parents[1]
RENEWALS = ROOT / 'data' / 'financial-products' / 'renewals'
PUBLIC = ROOT / 'frontend' / 'src' / 'public-data' / 'financial-renewals.json'
CATALOG = ROOT / 'data' / 'financial-products' / 'discovery-extended-20261103.json'
REVIEWS = ROOT / 'data' / 'financial-products' / 'verified-basic-rates-extended-20261103.json'
KST = timezone(timedelta(hours=9))
NUMBER = re.compile(r'(?<![\d.,])\d{1,2}\.\d{1,2}(?![\d.])')
ENDED = ('판매중단', '판매종료', '판매중지', '신규중단', '가입중단')
WINDOW = 2500
MIN_TEXT = 400


def _squash(text: str) -> str:
    return re.sub(r'\s+', '', text)


def name_on_page(name: str, text: str) -> tuple[bool, bool]:
    """(found, ended). The part before ' · ' is the product's own name; the rest is our variant label."""
    core = _squash(name.split(' · ')[0])
    flat = _squash(text)
    index = flat.find(core)
    if index < 0:
        return False, False
    ended = False
    while index >= 0:
        tail = flat[index + len(core): index + len(core) + 24]
        if any(marker in tail for marker in ENDED):
            ended = True
        else:
            return True, False  # at least one plain listing of the product
        index = flat.find(core, index + 1)
    return True, ended


def _numbers(text: str) -> list[tuple[int, Decimal]]:
    found = []
    for match in NUMBER.finditer(text):
        try:
            found.append((match.start(), Decimal(match.group()).quantize(Decimal('0.01'))))
        except InvalidOperation:
            continue
    return found


def _ordered_span(numbers: list[tuple[int, Decimal]], wanted: list[Decimal]) -> int | None:
    """Smallest character span in which `wanted` occurs as an ordered subsequence."""
    best = None
    for start, (position, value) in enumerate(numbers):
        if value != wanted[0]:
            continue
        need, last = 1, position
        for later_position, later_value in numbers[start + 1:]:
            if need == len(wanted) or later_position - position > WINDOW:
                break
            if later_value == wanted[need]:
                need, last = need + 1, later_position
        if need == len(wanted) and (best is None or last - position < best):
            best = last - position
    return best


def rates_on_page(rates: list[dict], text: str) -> tuple[bool, str]:
    """True when the stored base rates appear in term order (either direction) within WINDOW chars."""
    wanted = [Decimal(r['base_rate_percent']).quantize(Decimal('0.01')) for r in sorted(rates, key=lambda r: r['min_months'])]
    numbers = _numbers(text)
    if len(wanted) == 1:
        for position, value in numbers:
            if value == wanted[0] and re.search(r'기본|약정|금리|이율', text[max(0, position - 120): position]):
                return True, 'single rate next to a rate label'
        return False, 'single stored rate not found next to a rate label'
    collapsed = [v for i, v in enumerate(wanted) if i == 0 or v != wanted[i - 1]]
    for label, sequence in (('all rows', wanted), ('merged equal rows', collapsed)):
        if len(sequence) < 2:
            continue
        for direction, candidate in (('ascending terms', sequence), ('descending terms', sequence[::-1])):
            span = _ordered_span(numbers, candidate)
            if span is not None:
                return True, f'{len(sequence)} rates in order ({label}, {direction}) within {span} characters'
    return False, 'stored rate sequence not found in order'


def latest_entries() -> dict[str, tuple[str, dict]]:
    latest: dict[str, tuple[str, dict]] = {}
    for path in sorted(RENEWALS.glob('*/*.json')):
        batch = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(batch, dict) or 'updates' not in batch:
            continue
        for entry in batch['updates']:
            pid = entry['product']['product_id']
            if pid not in latest or batch['checked_on'] >= latest[pid][0]:
                latest[pid] = (batch['checked_on'], entry)
    return latest


def source_url(product: dict) -> str | None:
    pages = [s['url'] for s in product['sources'] if s.get('mode') == 'OFFICIAL_PAGE']
    return (pages or [s['url'] for s in product['sources']] or [None])[0]


def evaluate(today: date, get_text, only: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Return (updates, report rows). `get_text(url)` returns page text or raises."""
    renewals = json.loads(PUBLIC.read_text(encoding='utf-8'))
    latest = latest_entries()
    updates, report = [], []
    for row in recommendable(renewals):
        pid = row['product_id']
        if only and pid not in only:
            continue
        checked_on, entry = latest.get(pid, (None, None))
        result = {'product_id': pid, 'institution': row['institution'], 'product_name': row['product_name'], 'valid_until': row['valid_until']}
        if entry is None:
            report.append({**result, 'outcome': 'SKIP', 'detail': 'no batch entry found'})
            continue
        if checked_on == today.isoformat():
            report.append({**result, 'outcome': 'SKIP', 'detail': 'already checked today'})
            continue
        product = entry['product']
        url = source_url(product)
        try:
            text = get_text(url)
        except Exception as error:  # network, timeout, blocked: leave the record to expire
            report.append({**result, 'outcome': 'UNREADABLE', 'detail': f'{type(error).__name__}: {str(error)[:140]}', 'url': url})
            continue
        if len(_squash(text)) < MIN_TEXT:
            report.append({**result, 'outcome': 'UNREADABLE', 'detail': 'page text too short', 'url': url})
            continue
        found, ended = name_on_page(product['product_name'], text)
        if not found or ended:
            report.append({**result, 'outcome': 'MISMATCH', 'detail': 'sales-ended marker after the name' if ended else 'product name not on page', 'url': url})
            continue
        ok, detail = rates_on_page(product['rates'], text)
        if not ok:
            report.append({**result, 'outcome': 'MISMATCH', 'detail': detail, 'url': url})
            continue
        new = copy.deepcopy(entry)
        note = (f'automated comparison on {today.isoformat()} (not a human reading): the rendered official page shows the product name '
                f'and the stored base rates ({detail}); no sales-ended marker follows the name. Only this source was read.')
        for part in (new['product'], new['review']):
            kept = [s for s in part['sources'] if s['url'] == url]
            for source in kept:
                source['reviewed_on'] = today.isoformat()
                source['title'] = (source['title'].split(' (자동 대조')[0] + ' (자동 대조)')[:200]
                source['locator'] = f'자동 대조 {today.isoformat()}: {detail}'
            part['sources'] = kept
            for rate in part['rates']:
                rate['evidence_locator'] = f'자동 대조 {today.isoformat()}: {detail}'
        new['evidence_note'] = note
        new['change_notes'] = []
        updates.append(new)
        report.append({**result, 'outcome': 'RENEWED', 'detail': detail, 'url': url})
    return updates, report


def browser_text_getter():
    """Lazy import so tests and --help work without Playwright."""
    from playwright.sync_api import sync_playwright
    manager = sync_playwright().start()
    browser = manager.chromium.launch()
    context = browser.new_context(locale='ko-KR', viewport={'width': 1366, 'height': 900},
                                  user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36')

    def get(url: str) -> str:
        if url.lower().split('?')[0].endswith('.pdf'):
            from pypdf import PdfReader
            response = context.request.get(url, timeout=45000)
            if not response.ok:
                raise RuntimeError(f'HTTP {response.status}')
            return '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(response.body())).pages)
        page = context.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            try:
                page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            parts = []
            for frame in page.frames:
                try:
                    parts.append(frame.evaluate("() => document.body ? document.body.textContent : ''"))
                except Exception:
                    continue
            return '\n'.join(parts)
        finally:
            page.close()

    def close():
        browser.close()
        manager.stop()

    return get, close


def write_outputs(today: date, updates: list[dict]) -> Path:
    from backend.finance.discovery import load_catalog
    from backend.finance.renewal import compile_renewals
    folder = RENEWALS / today.strftime('%Y%m%d')
    folder.mkdir(parents=True, exist_ok=True)
    batch = {'checked_on': today.isoformat(), 'updates': updates, 'holds': [], 'actual_maturity_calculations': 0,
             'scope_note': 'Automated comparison of stored base rates against the rendered official page (tools/auto_recheck.py). Not a human reading; unchanged products only.'}
    path = folder / 'auto-reviewed.json'
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    batches = []
    for file in sorted(RENEWALS.glob('*/*.json')):
        data = json.loads(file.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'updates' in data:
            batches.append(data)
    reviews = {e['product_id']: e for e in json.loads(REVIEWS.read_text(encoding='utf-8'))['entries']}
    result = compile_renewals(load_catalog(CATALOG), reviews, batches, today)
    PUBLIC.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--today', help='YYYY-MM-DD (default: today in KST)')
    parser.add_argument('--dry-run', action='store_true', help='compare only; change no data')
    parser.add_argument('--report', type=Path, help='write the per-product outcome list here')
    parser.add_argument('--only', help='comma-separated product ids')
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(KST).date()
    get, close = browser_text_getter()
    try:
        updates, report = evaluate(today, get, set(args.only.split(',')) if args.only else None)
    finally:
        close()
    counts: dict[str, int] = {}
    for row in report:
        counts[row['outcome']] = counts.get(row['outcome'], 0) + 1
    print(json.dumps({'today': today.isoformat(), 'counts': counts}, ensure_ascii=False))
    for row in report:
        print(f"{row['outcome']:<10} {row['product_id']:<28} {row['detail']}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'today': today.isoformat(), 'counts': counts, 'rows': report}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if args.dry_run or not updates:
        return 0
    print(f'wrote {write_outputs(today, updates)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
