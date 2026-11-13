"""Automated page comparison for youth support programs (not a human reading).

For every program that is not closed, open its official source pages and renew the
program only when one page still shows the program name, the published deadline
(for dated application windows) and no closing marker next to the name. Anything
else stays as it was and the app keeps showing "최신 공고 재확인".

Output: data/support-programs/rechecks/<YYYYMMDD>.json, read by
backend/opportunities/current_discovery.py when the public file is rebuilt.

Usage (repo root):
  python tools/support_recheck.py [--date YYYY-MM-DD] [--only ID ...] [--concurrency 6]
  python tools/support_recheck.py --dry-run --report report.json   # compare only, data unchanged
  python -m backend.opportunities.current_discovery   # rebuild the public file
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RECHECKS = ROOT / 'data' / 'support-programs' / 'rechecks'
KST = timezone(timedelta(hours=9))
MIN_TEXT = 200
# Closing labels shown next to a listing. "조기마감" is left out: it usually appears
# as the caveat "예산 소진 시 조기마감".
CLOSED_MARKERS = ('모집마감', '접수마감', '신청마감', '모집종료', '접수종료', '신청종료',
                  '마감되었', '종료되었', '마감된', '종료된', '사업종료', '모집완료', '접수완료')
# Bracketed status labels on listings, e.g. "[조기마감] 사업명" or "사업명 (마감)".
# A bracket holding other words, e.g. "[예산 소진 시 조기마감]", is a caveat, not a label.
CLOSED_LABELS = ('[마감]', '[조기마감]', '(마감)', '[종료]', '(종료)', '[접수마감]', '[모집마감]')
# "신청마감일 12.4" or "접수마감: 12월" describe the deadline, not a closed state.
# A following particle ("신청마감은 … 안내 예정") also marks a sentence about the deadline.
NOT_STATE = ('일', '기한', '시간', '날짜', ':', '：', '(', '2', '1', '0', '은', '는', '이', '시', '후')
NEAR = 40


def squash(text: str) -> str:
    return re.sub(r'\s+', '', text or '')


def name_variants(title: str) -> list[str]:
    """Program name as written in our data, and without a leading place name."""
    core = title.split(' · ')[0].strip()
    variants = [squash(core)]
    words = core.split()
    if len(words) > 1:
        # Our titles often start with the place ("군포", "나주시"); official pages may not repeat it.
        rest = squash(' '.join(words[1:]))
        if len(rest) >= 5:
            variants.append(rest)
    year_free = re.sub(r'^\d{4}년?', '', variants[0])
    if year_free != variants[0] and len(year_free) >= 6:
        variants.append(year_free)
    return list(dict.fromkeys(variants))


def find_name(title: str, flat: str) -> tuple[bool, bool]:
    """(found, closed). Closed if any mention of the name has a closing label next to it:
    a detail page often shows "[조기마감] 사업명" once and repeats the plain name in the body."""
    found = closed = False
    for variant in name_variants(title):
        start = flat.find(variant)
        while start >= 0:
            found = True
            window = flat[max(0, start - NEAR): start] + '|' + flat[start + len(variant): start + len(variant) + NEAR]
            closed = closed or closing_marker(window)
            start = flat.find(variant, start + 1)
    return found, closed


def closing_marker(window: str) -> bool:
    if any(label in window for label in CLOSED_LABELS):
        return True
    for marker in CLOSED_MARKERS:
        at = window.find(marker)
        while at >= 0:
            nxt = window[at + len(marker): at + len(marker) + 1]
            if not nxt or nxt not in NOT_STATE:
                return True
            at = window.find(marker, at + 1)
    return False


def date_on_page(iso: str, flat: str) -> bool:
    """The deadline in any common Korean notation: 2026.12.04, 2026-12-4, 12.4, 12월 4일, 12/4."""
    y, m, d = (int(x) for x in iso.split('-'))
    mm, dd = rf'0?{m}', rf'0?{d}'
    patterns = (
        rf'{y}[.\-/년]{mm}[.\-/월]{dd}(?!\d)',
        rf'(?<![\d.]){mm}\.{dd}(?![\d])',
        rf'(?<!\d){mm}월{dd}일',
        rf'(?<![\d/]){mm}/{dd}(?![\d/])',
    )
    return any(re.search(p, flat) for p in patterns)


def compare(program: dict, text: str) -> tuple[str, str]:
    """(result, reason) for one page. result: MATCH, CLOSED_SIGNAL, NO_NAME, NO_DATE, TOO_SHORT."""
    flat = squash(text)
    if len(flat) < MIN_TEXT:
        return 'TOO_SHORT', '페이지 본문이 거의 비어 있음(로그인·차단 가능)'
    found, closed = find_name(program['title'], flat)
    if not found:
        return 'NO_NAME', '사업명이 보이지 않음'
    if closed:
        return 'CLOSED_SIGNAL', '사업명 옆에 마감·종료 표시'
    if program['intake_mode'] == 'WINDOW' and program.get('ends_on') and not date_on_page(program['ends_on'], flat):
        return 'NO_DATE', '공고 마감일이 보이지 않음'
    return 'MATCH', '사업명' + ('·마감일' if program['intake_mode'] == 'WINDOW' and program.get('ends_on') else '') + ' 일치, 마감·종료 표시 없음'


def targets(today: date, only: set[str] | None = None) -> list[dict]:
    from backend.opportunities.current_discovery import current_inputs
    catalog, _, _ = current_inputs(use_rechecks=False)
    rows = []
    for p in catalog.programs:
        if only and p.program_id not in only:
            continue
        if p.intake_mode in ('CLOSED', 'NO_INTAKE'):
            continue
        if p.ends_on and date.fromisoformat(p.ends_on) < today:
            continue
        rows.append(p.model_dump(mode='json'))
    return rows


def evaluate(programs: list[dict], texts: dict[str, str | Exception]) -> list[dict]:
    results = []
    for p in programs:
        pages = []
        for s in p['sources']:
            text = texts.get(s['url'])
            if isinstance(text, Exception) or text is None:
                pages.append(dict(url=s['url'], result='FETCH_FAILED', reason=str(text)[:120] if text else '열지 않음'))
                continue
            result, reason = compare(p, text)
            pages.append(dict(url=s['url'], result=result, reason=reason))
        if any(x['result'] == 'CLOSED_SIGNAL' for x in pages):
            status = 'CLOSED_SIGNAL'
        elif any(x['result'] == 'MATCH' for x in pages):
            status = 'RENEWED'
        else:
            status = 'NOT_MATCHED'
        results.append(dict(program_id=p['program_id'], title=p['title'], status=status, pages=pages))
    return results


async def fetch_all(urls: list[str], concurrency: int, timeout: int = 25000) -> dict[str, str | Exception]:
    from playwright.async_api import async_playwright
    out: dict[str, str | Exception] = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(locale='ko-KR', viewport={'width': 1366, 'height': 900}, ignore_https_errors=False,
                                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36')
        gate = asyncio.Semaphore(concurrency)

        async def one(url: str):
            async with gate:
                try:
                    if url.lower().split('?')[0].endswith('.pdf'):
                        from pypdf import PdfReader
                        response = await context.request.get(url, timeout=timeout)
                        if not response.ok:
                            raise RuntimeError(f'HTTP {response.status}')
                        body = await response.body()
                        out[url] = '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(body)).pages)
                        return
                    page = await context.new_page()
                    try:
                        response = await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                        if response is not None and response.status >= 400:
                            raise RuntimeError(f'HTTP {response.status}')
                        try:
                            await page.wait_for_load_state('networkidle', timeout=6000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(800)
                        parts = []
                        for frame in page.frames:
                            try:
                                parts.append(await frame.evaluate("() => document.body ? document.body.innerText : ''"))
                            except Exception:
                                continue
                        out[url] = '\n'.join(parts)
                    finally:
                        await page.close()
                except Exception as error:  # recorded per page; never stops the run
                    out[url] = RuntimeError(type(error).__name__ + ': ' + str(error).splitlines()[0][:100])

        await asyncio.gather(*(one(u) for u in urls))
        await browser.close()
    return out


def write(today: date, results: list[dict], path: Path | None = None) -> Path:
    if path is None:
        RECHECKS.mkdir(parents=True, exist_ok=True)
        path = RECHECKS / f'{today:%Y%m%d}.json'
    counts = {k: sum(r['status'] == k for r in results) for k in ('RENEWED', 'NOT_MATCHED', 'CLOSED_SIGNAL')}
    payload = dict(
        schema_version='support-recheck-v1', checked_on=today.isoformat(),
        method='자동 대조: 공식 출처 페이지를 열어 사업명·공고 마감일·마감 표시를 비교함. 사람이 읽은 확인이 아님.',
        counts=counts, results=sorted(results, key=lambda r: r['program_id']))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--date', help='check date (default: today in KST)')
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--concurrency', type=int, default=6)
    parser.add_argument('--dry-run', action='store_true', help='compare only; write the report to --report, not to the data folder')
    parser.add_argument('--report', type=Path, help='also write the results here (required with --dry-run)')
    args = parser.parse_args(argv)
    if args.dry_run and not args.report:
        parser.error('--dry-run needs --report')
    today = date.fromisoformat(args.date) if args.date else datetime.now(KST).date()
    programs = targets(today, set(args.only) if args.only else None)
    urls = sorted({s['url'] for p in programs for s in p['sources']})
    print(f'programs {len(programs)} · pages {len(urls)}', flush=True)
    texts = asyncio.run(fetch_all(urls, args.concurrency))
    # Slow or busy public sites (often from overseas CI runners): one slower retry for pages that failed.
    failed = [u for u, t in texts.items() if isinstance(t, Exception)]
    if failed:
        retried = asyncio.run(fetch_all(failed, 2, timeout=45000))
        texts.update({u: t for u, t in retried.items() if not isinstance(t, Exception)})
        print(f'retried {len(failed)} · recovered {sum(not isinstance(t, Exception) for t in retried.values())}', flush=True)
    results = evaluate(programs, texts)
    if args.report:
        write(today, results, args.report)
    path = args.report if args.dry_run else write(today, results)
    print(json.dumps(dict(file=str(path), dry_run=args.dry_run, **{k: sum(r['status'] == k for r in results) for k in ('RENEWED', 'NOT_MATCHED', 'CLOSED_SIGNAL')}), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
