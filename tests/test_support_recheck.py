from datetime import date
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from support_recheck import compare, date_on_page, evaluate, find_name, name_variants, squash  # noqa: E402
from backend.opportunities.current_discovery import apply_recheck_results  # noqa: E402
from backend.opportunities.regional_discovery import Program, recruitment  # noqa: E402

FILLER = '청년 정책 안내 페이지입니다. ' * 30


def program(**kw):
    base = dict(program_id='T-1', title='군포 마음든든 첫만남 · 육아 청년 프로그램', intake_mode='WINDOW', ends_on='2026-11-17',
                sources=[dict(url='https://a.go.kr/1', title='공고', basis_date=None, verified_on='2026-11-01', evidence='OFFICIAL_PAGE', locator='본문'),
                         dict(url='https://b.go.kr/2', title='신청', basis_date=None, verified_on='2026-11-01', evidence='OFFICIAL_PAGE', locator='신청 페이지')])
    base.update(kw)
    return base


def test_name_variants_drop_place_and_variant_label():
    assert name_variants('군포 마음든든 첫만남 · 육아 청년 프로그램') == ['군포마음든든첫만남', '마음든든첫만남']
    assert name_variants('의령군 청년 시험응시료 지원')[0] == '의령군청년시험응시료지원'
    assert '광산구구직청년자격증취득비용지원사업' in name_variants('2026년 광산구 구직청년 자격증 취득비용 지원사업')


@pytest.mark.parametrize('text,closed', [
    ('프로그램신청 [조기마감] 마음든든 첫만남 - 육아청년 마감', True),
    ('[조기마감] 마음든든 첫만남 안내 ... 본문 ' + '가' * 60 + ' 마음든든 첫만남 신청 방법', True),  # one closed mention is enough
    ('마음든든 첫만남 모집종료', True),
    ('마음든든 첫만남 신청마감일 11.17. 예산 소진 시 조기마감', False),
    ('마음든든 첫만남 접수중 신청기간 11.17', False),
    ('(미추홀구)마음든든 첫만남 지원사업[예산소진시조기마감] 접수중', False),
    ('마음든든 첫만남 예산소진시 신청마감은 별도 안내 예정', False),
])
def test_closing_labels_next_to_the_name(text, closed):
    found, is_closed = find_name('군포 마음든든 첫만남 · 육아 청년 프로그램', squash(text))
    assert found and is_closed is closed


@pytest.mark.parametrize('text', ['신청기간: 2026.10.28.~2026.11.17.', '2026-11-17까지', '~ 11. 17.', '11월 17일(월) 18시', '10/28~11/17'])
def test_deadline_in_common_notations(text):
    assert date_on_page('2026-11-17', squash(text))


@pytest.mark.parametrize('text', ['11.170명', '2026.11.1', '11월 1일', '111/17'])
def test_deadline_does_not_match_other_numbers(text):
    assert not date_on_page('2026-11-17', squash(text))


def test_compare_requires_name_date_and_no_closing_label():
    p = program()
    assert compare(p, '짧음')[0] == 'TOO_SHORT'
    assert compare(p, FILLER + '다른 사업 안내')[0] == 'NO_NAME'
    assert compare(p, FILLER + '마음든든 첫만남 참여자 모집')[0] == 'NO_DATE'
    assert compare(p, FILLER + '마음든든 첫만남 신청기간 2026.10.28.~11.17.')[0] == 'MATCH'
    assert compare(p, FILLER + '[마감] 마음든든 첫만남 신청기간 2026.10.28.~11.17.')[0] == 'CLOSED_SIGNAL'
    assert compare(program(intake_mode='CONTINUOUS', ends_on=None), FILLER + '마음든든 첫만남 상시 접수')[0] == 'MATCH'


def test_any_closed_page_blocks_renewal_and_failures_are_recorded():
    p = program()
    match = FILLER + '마음든든 첫만남 신청기간 ~11.17.'
    assert evaluate([p], {'https://a.go.kr/1': match, 'https://b.go.kr/2': RuntimeError('HTTP 403')})[0]['status'] == 'RENEWED'
    assert evaluate([p], {'https://a.go.kr/1': match, 'https://b.go.kr/2': FILLER + '[조기마감] 마음든든 첫만남'})[0]['status'] == 'CLOSED_SIGNAL'
    result = evaluate([p], {'https://a.go.kr/1': FILLER, 'https://b.go.kr/2': RuntimeError('HTTP 403')})[0]
    assert result['status'] == 'NOT_MATCHED'
    assert [x['result'] for x in result['pages']] == ['NO_NAME', 'FETCH_FAILED']


def test_renewed_pages_are_added_as_automated_sources_without_touching_reviewed_ones():
    p = program()
    records = {'T-1': p}
    latest = {'T-1': ('2026-11-13', dict(status='RENEWED', pages=[dict(url='https://b.go.kr/2', result='MATCH', reason='사업명·마감일 일치, 마감·종료 표시 없음'),
                                                               dict(url='https://a.go.kr/1', result='NO_NAME', reason='사업명이 보이지 않음')]))}
    apply_recheck_results(records, latest)
    added, *kept = records['T-1']['sources']
    assert added['url'] == 'https://b.go.kr/2' and added['evidence'] == 'AUTOMATED_PAGE_MATCH' and added['verified_on'] == '2026-11-13'
    assert '사람이 읽은 확인 아님' in added['locator'] and added['title'] == '신청 · 자동 대조'
    assert kept == program()['sources']  # reviewed sources keep their dates, so past days are unchanged


@pytest.mark.parametrize('status', ['NOT_MATCHED', 'CLOSED_SIGNAL'])
def test_unrenewed_results_change_nothing(status):
    records = {'T-1': program()}
    apply_recheck_results(records, {'T-1': ('2026-11-13', dict(status=status, pages=[dict(url='https://a.go.kr/1', result='MATCH', reason='x')]))})
    assert records['T-1'] == program()


def full_program(sources):
    return Program.model_validate(dict(
        program_id='T-1', title='테스트 사업', authority='테스트시', edition='2026', category='LIVING', provinces=[], city=None,
        benefit_summary='요약', age_note='나이', income_note='소득', required_checks=['확인'], schedule_note='일정',
        starts_on='2026-10-01', ends_on='2026-12-31', intake_mode='WINDOW', sources=sources, aliases=[],
        data_status='DRAFT', coverage='CONDITION_SLICE', eligibility='UNKNOWN', benefit_applied_krw=0))


def test_an_automated_match_keeps_the_program_fresh_for_the_review_window_only():
    old = dict(url='https://a.go.kr/1', title='공고', basis_date=None, verified_on='2026-11-01', evidence='OFFICIAL_PAGE', locator='본문')
    auto = {**old, 'url': 'https://b.go.kr/2', 'verified_on': '2026-11-13', 'evidence': 'AUTOMATED_PAGE_MATCH'}
    p = full_program([auto, old])
    assert recruitment(p, date(2026, 11, 1)) == 'WINDOW_GUIDANCE'  # the reviewed source alone, as before
    assert recruitment(p, date(2026, 11, 9)) == 'REVIEW_REQUIRED'  # before the automated check
    assert recruitment(p, date(2026, 11, 13)) == 'WINDOW_GUIDANCE'
    assert recruitment(p, date(2026, 11, 20)) == 'WINDOW_GUIDANCE'
    assert recruitment(p, date(2026, 11, 21)) == 'REVIEW_REQUIRED'
    assert recruitment(full_program([{**auto, 'evidence': 'OFFICIAL_PAGE'}, old]), date(2026, 11, 13)) == 'REVIEW_REQUIRED'  # old rule unchanged
