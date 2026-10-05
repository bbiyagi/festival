from datetime import date

import pytest

from api import festival_rules as r


def test_to_iso_date() -> None:
    assert r.to_iso_date("20261005") == date(2026, 10, 5)
    assert r.to_iso_date("") is None
    assert r.to_iso_date(None) is None
    assert r.to_iso_date("20261332") is None
    assert r.to_iso_date("2026-10-05") is None


@pytest.mark.parametrize(
    ("addr", "code", "region"),
    [
        ("서울특별시 중구 정동길 3", None, "seoul"),
        ("경기도 고양시 일산동구", None, "gyeonggi"),
        ("인천 중구", None, "gyeonggi"),
        ("강원특별자치도 춘천시", None, "gangwon"),
        ("충청남도 논산시 강경읍", None, "chungcheong"),
        ("대전광역시 유성구", None, "chungcheong"),
        ("세종특별자치시 다솜로 216", None, "chungcheong"),
        ("전북특별자치도 전주시", None, "jeolla"),
        ("전남광주통합특별시 곡성군 오곡면", None, "jeolla"),
        ("광주광역시 동구", None, "jeolla"),
        ("경상북도 경주시", None, "gyeongbuk"),
        ("대구광역시 중구", None, "gyeongbuk"),
        ("경상남도 거창군", None, "gyeongnam"),
        ("부산 기장군 장안읍", None, "gyeongnam"),
        ("울산광역시 남구", None, "gyeongnam"),
        ("제주특별자치도 서귀포시", None, "jeju"),
        ("", "12", "jeolla"),
        (None, "36110", "chungcheong"),
        ("", "", None),
        ("알 수 없는 곳", "99", None),
    ],
)
def test_region_of(addr: str | None, code: str | None, region: str | None) -> None:
    assert r.region_of(addr, code) == region


@pytest.mark.parametrize(
    ("addr", "place", "town"),
    [
        ("충청남도 논산시 강경읍 황산리 198", "충남 논산시", "논산"),
        ("서울특별시 중구 정동길 3 (정동)", "서울 중구", "중구"),
        ("서울특별시 강남구 도산대로 320", "서울 강남구", "강남"),
        ("경상남도 거창군 신원면", "경남 거창군", "거창"),
        ("강원특별자치도 고성군 거진읍", "강원 고성군", "고성"),
        ("전남광주통합특별시 곡성군 오곡면", "전남광주 곡성군", "곡성"),
        ("부산 기장군 장안읍", "부산 기장군", "기장"),
        ("세종특별자치시 다솜로 216 (세종동)", "세종", "세종"),
        ("제주특별자치도 서귀포시 안덕면", "제주 서귀포시", "서귀포"),
        ("", None, None),
    ],
)
def test_place_and_town(addr: str, place: str | None, town: str | None) -> None:
    assert r.place_of(addr) == place
    assert r.town_of(addr) == town


def test_is_always() -> None:
    assert r.is_always(date(2026, 1, 1), date(2026, 12, 31))
    assert r.is_always(date(2022, 11, 1), date(2026, 12, 31))
    assert not r.is_always(date(2026, 5, 6), date(2026, 12, 31))
    assert not r.is_always(None, date(2026, 12, 31))


def test_overlaps() -> None:
    week = (date(2026, 10, 5), date(2026, 10, 11))
    assert r.overlaps(date(2026, 9, 18), date(2026, 10, 5), *week)  # 기간 첫날에 끝남
    assert r.overlaps(date(2026, 10, 11), date(2026, 10, 20), *week)  # 기간 마지막 날 시작
    assert r.overlaps(date(2026, 1, 1), date(2026, 12, 31), *week)
    assert not r.overlaps(date(2026, 9, 1), date(2026, 10, 4), *week)
    assert not r.overlaps(date(2026, 10, 12), date(2026, 10, 13), *week)
    assert not r.overlaps(None, date(2026, 10, 6), *week)


def test_clean_text() -> None:
    assert r.clean_text("첫 줄<br>둘째 줄<BR />셋째") == "첫 줄\n둘째 줄\n셋째"
    assert r.clean_text('<a href="x">링크</a> &amp; <b>굵게</b>') == "링크 & 굵게"
    assert r.clean_text("<script>alert(1)</script>") == "alert(1)"
    assert r.clean_text("") is None
    assert r.clean_text("<br>") is None


@pytest.mark.parametrize(
    ("raw", "text"),
    [
        ("10:00~20:00", "10:00~20:00"),
        ("- 09:00~18:00※ 매주 화요일 휴관", "09:00~18:00※ 매주 화요일 휴관"),
        ("- 평일 19:30<br>- 주말 15:00", "평일 19:30 / 주말 15:00"),
        ("<br>", None),
        (None, None),
    ],
)
def test_playtime_of(raw: str | None, text: str | None) -> None:
    assert r.playtime_of(raw) == text


def test_homepage_url() -> None:
    a = '<a href="https://www.nonsan.go.kr/ggfestival/" target="_blank">홈페이지</a>'
    assert r.homepage_url(a) == "https://www.nonsan.go.kr/ggfestival/"
    assert r.homepage_url("https://example.com/a?b=1") == "https://example.com/a?b=1"
    assert r.homepage_url("www.example.com") is None
    assert r.homepage_url("") is None


@pytest.mark.parametrize(
    ("code", "kind", "category"),
    [
        ("EV010300", "festival", "지역특산물축제"),
        ("EV020700", "show", "대중콘서트"),
        ("EV030100", "exhibit", "전시회"),
        ("EV030200", "exhibit", "박람회"),
        ("EV030400", "event", "기타행사"),
        ("EV030900", "event", None),  # 새 코드: 묶음은 알고 이름은 모름
        ("", None, None),
        (None, None, None),
    ],
)
def test_kind_and_category(code: str | None, kind: str | None, category: str | None) -> None:
    assert r.kind_of(code) == kind
    assert r.CATEGORY.get(code or "") == category


@pytest.mark.parametrize(
    ("tel", "phone"),
    [
        ("055-940-8227", "055-940-8227"),
        ("041-730-2971, 2973", "041-730-2971"),
        ("055-670-7491~3", "055-670-7491"),
        ("1522-2295", "1522-2295"),
        ("02-3423-5543", "02-3423-5543"),
        ("문의 없음", None),
        ("", None),
        (None, None),
    ],
)
def test_phone_of(tel: str | None, phone: str | None) -> None:
    assert r.phone_of(tel) == phone


@pytest.mark.parametrize(
    ("fee", "price"),
    [
        ("무료", "free"),
        ("입장료 무료 (일부 체험, 홍보판매 푸드트럭 등 유료)", "partial"),
        ("유료(셔틀버스 이용료 3,000원)", "paid"),
        ("- VIP석 70,000원- R석 60,000원", "paid"),
        ("현장 문의", None),
        ("", None),
        (None, None),
    ],
)
def test_price_of(fee: str | None, price: str | None) -> None:
    assert r.price_of(fee) == price


def test_normalize_festival_missing_fields() -> None:
    f = r.normalize_festival({"contentid": "1", "title": " 이름 "})
    assert f == {
        "id": "1",
        "title": "이름",
        "place": None,
        "place_detail": None,
        "town": None,
        "region": None,
        "category": None,
        "kind": None,
        "start": None,
        "end": None,
        "is_always": False,
        "image": None,
        "thumb": None,
        "tel": None,
        "lat": None,
        "lng": None,
    }
