import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from youthcenter_fetch import city_name, homepage, normalise, phone, province_key, write_if_changed  # noqa: E402

CITIES = json.loads((Path(__file__).resolve().parents[1] / 'frontend/src/public-data/nationwide-districts.json').read_text(encoding='utf-8'))['cities']


def record(**kw):
    base = dict(cntrSn='10326', cntrNm='동래구청년어울림센터', cntrAddr='부산광역시동래구금강로', cntrDaddr='129', cntrTelno='051-997-5003',
                cntrUrlAddr='', stdgCtpvCd='26', stdgCtpvCdNm='부산광역시', stdgSggCd='260', stdgSggCdNm='동래구')
    base.update(kw)
    return base


def test_province_names_map_to_app_regions():
    assert province_key('부산광역시') == '부산'
    assert province_key('강원특별자치도') == '강원'
    assert province_key('전북특별자치도') == '전북'
    assert province_key('세종특별자치시') == '세종'
    assert province_key('경상남도') == '경남'
    assert province_key('충청북도') == '충북'
    assert province_key('경기도') == '경기'
    assert province_key('없는도') is None


def test_city_names_match_options_including_wards():
    assert city_name('부산', '동래구', CITIES) == '동래구'
    assert city_name('경기', '안산시 단원구', CITIES) == '안산시 단원구'
    assert city_name('경기', '안산시단원구', CITIES) == '안산시 단원구'
    assert city_name('경기', '의정부시', CITIES) == '의정부시'
    assert city_name('경기', '수원시 없는구', CITIES) == '수원시'
    assert city_name('세종', '세종시', CITIES) == ''
    assert city_name('경기', '', CITIES) == ''


def test_phone_and_homepage_are_kept_only_when_usable():
    assert phone('051-997-5003') == '051-997-5003'
    assert phone('') is None and phone('없음') is None
    assert homepage('https://hsyouthcenter.hsg.go.kr/') == 'https://hsyouthcenter.hsg.go.kr/'
    assert homepage('www.example.kr') == 'https://www.example.kr'
    assert homepage('') is None and homepage('javascript:alert(1)') is None


def test_normalise_keeps_needed_fields_drops_duplicates_and_bad_rows():
    rows = [record(), record(), record(cntrSn='2', cntrNm='횡성군 청년센터', stdgCtpvCdNm='강원특별자치도', stdgSggCdNm='횡성군', cntrUrlAddr='https://hsyouthcenter.hsg.go.kr/'),
            record(cntrSn='3', stdgCtpvCdNm=''), record(cntrSn='', cntrNm='x')]
    out = normalise(rows, CITIES)
    assert [c['id'] for c in out] == ['YC-2', 'YC-10326']
    busan = out[1]
    assert busan == {'id': 'YC-10326', 'province': '부산', 'city': '동래구', 'district_label': '동래구', 'name': '동래구청년어울림센터',
                     'address': '부산광역시동래구금강로 129', 'phone': '051-997-5003', 'url': None}


def test_write_only_when_centers_change(tmp_path):
    out = tmp_path / 'c.json'
    centers = normalise([record()], CITIES)
    assert write_if_changed(out, centers, '2026-11-16') is True
    assert write_if_changed(out, centers, '2026-11-17') is False
    assert json.loads(out.read_text(encoding='utf-8'))['fetched_on'] == '2026-11-16'
    assert write_if_changed(out, normalise([record(cntrTelno='051-000-0000')], CITIES), '2026-11-17') is True
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['fetched_on'] == '2026-11-17' and data['source']['attribution'] == '출처: 온통청년(한국고용정보원)'
