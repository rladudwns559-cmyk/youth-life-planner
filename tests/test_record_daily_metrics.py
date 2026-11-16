import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from record_daily_metrics import record_ontong, record_support  # noqa: E402


def policies(path: Path, ids):
    path.write_text(json.dumps({'policies': [{'id': i} for i in ids]}), encoding='utf-8')
    return path


def test_ontong_counts_new_and_removed_and_adds_up_within_a_day(tmp_path):
    out = tmp_path / 'm.json'
    centers = tmp_path / 'c.json'
    centers.write_text(json.dumps({'centers': [1, 2, 3]}), encoding='utf-8')
    first = record_ontong(tmp_path / 'missing.json', policies(tmp_path / 'a.json', ['A', 'B']), centers, '2026-11-16', out)
    assert first == {'date': '2026-11-16', 'policies': 2, 'new': None, 'removed': None, 'centers': 3}
    row = record_ontong(tmp_path / 'a.json', policies(tmp_path / 'b.json', ['B', 'C', 'D']), None, '2026-11-17', out)
    assert row == {'date': '2026-11-17', 'policies': 3, 'new': 2, 'removed': 1}
    again = record_ontong(tmp_path / 'b.json', policies(tmp_path / 'c2.json', ['B', 'C', 'D', 'E']), None, '2026-11-17', out)
    assert again['new'] == 3 and again['removed'] == 1 and again['policies'] == 4
    data = json.loads(out.read_text(encoding='utf-8'))
    assert [d['date'] for d in data['days']] == ['2026-11-16', '2026-11-17']
    assert out.read_text(encoding='utf-8').count('\n') == 4  # one line per day


def test_support_reads_counts_and_replaces_a_rerun(tmp_path):
    out = tmp_path / 's.json'
    recheck = tmp_path / 'r.json'
    recheck.write_text(json.dumps({'checked_on': '2026-11-16', 'counts': {'RENEWED': 94, 'NOT_MATCHED': 20, 'CLOSED_SIGNAL': 2},
                                   'results': [{}] * 116}), encoding='utf-8')
    assert record_support(recheck, out) == {'date': '2026-11-16', 'checked': 116, 'renewed': 94, 'closed_signal': 2, 'not_matched': 20}
    recheck.write_text(json.dumps({'checked_on': '2026-11-16', 'counts': {'RENEWED': 95}, 'results': [{}] * 116}), encoding='utf-8')
    assert record_support(recheck, out)['renewed'] == 95
    assert len(json.loads(out.read_text(encoding='utf-8'))['days']) == 1


def test_first_day_stays_unknown_after_a_rerun(tmp_path):
    out = tmp_path / 'm.json'
    record_ontong(tmp_path / 'missing.json', policies(tmp_path / 'a.json', ['A']), None, '2026-11-16', out)
    again = record_ontong(tmp_path / 'a.json', policies(tmp_path / 'b.json', ['A', 'B']), None, '2026-11-16', out)
    assert again['new'] is None and again['removed'] is None and again['policies'] == 2
    nextday = record_ontong(tmp_path / 'b.json', policies(tmp_path / 'c.json', ['B', 'C']), None, '2026-11-17', out)
    assert nextday['new'] == 1 and nextday['removed'] == 1
