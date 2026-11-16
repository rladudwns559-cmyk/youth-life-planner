"""Read-only trial call of the 온통청년 Open APIs (youth policies, youth centers).

Runs in GitHub Actions with the keys from repository secrets. Writes a few sample
records and the response shape to the output folder so the integration can be designed
from real data. The key is sent only in the request and is never printed or written.

Usage: YOUTHCENTER_POLICY_KEY=... YOUTHCENTER_CENTER_KEY=... python tools/youthcenter_probe.py OUT_DIR
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINTS = {
    'policy': ('https://www.youthcenter.go.kr/go/ythip/getPlcy', 'YOUTHCENTER_POLICY_KEY'),
    'center': ('https://www.youthcenter.go.kr/go/ythip/getSpace', 'YOUTHCENTER_CENTER_KEY'),
}


def shape(value, depth=0):
    """Keys and types only, so the structure can be read without dumping everything."""
    if depth > 4:
        return '...'
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in list(value.items())[:80]}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def call(url: str, key: str, **params) -> tuple[int, str]:
    query = urllib.parse.urlencode({'apiKeyNm': key, 'rtnType': 'json', **params})
    request = urllib.request.Request(f'{url}?{query}', headers={'User-Agent': 'youth-life-planner-probe/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, response.read().decode('utf-8', errors='replace')


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'probe-out')
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, (url, env) in ENDPOINTS.items():
        key = os.environ.get(env, '').strip()
        if not key:
            summary[name] = {'error': f'{env} is not set'}
            continue
        try:
            status, body = call(url, key, pageNum=1, pageSize=5, pageType=1)
        except Exception as error:  # report the type only; messages can echo the URL
            summary[name] = {'error': type(error).__name__}
            continue
        if key in body:
            body = body.replace(key, '***')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            summary[name] = {'status': status, 'not_json_first_200_chars': body[:200]}
            continue
        (out / f'{name}-sample.json').write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
        summary[name] = {'status': status, 'shape': shape(data)}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: ({'status': v.get('status'), 'error': v.get('error')}) for k, v in summary.items()}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
