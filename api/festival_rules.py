"""축제 데이터 규칙: TourAPI 원본 값을 앱에서 쓰는 형태로 정리한다.

규칙을 바꾸면 tests/test_festival_rules.py도 함께 고친다.
"""

import html
import re
from datetime import date
from typing import Any

# 권역 id → 화면 이름은 Vue 쪽에서 붙인다. id는 Tailwind 권역 색 토큰과 같다.
REGIONS = (
    "seoul",
    "gyeonggi",
    "gangwon",
    "chungcheong",
    "jeolla",
    "gyeongbuk",
    "gyeongnam",
    "jeju",
)

# 주소 첫 단어의 앞부분 → 권역. 줄인 주소("부산")와 2026 통합 행정구역("전남광주통합특별시")도 포함.
_ADDR_PREFIX: tuple[tuple[str, str], ...] = (
    ("서울", "seoul"),
    ("경기", "gyeonggi"),
    ("인천", "gyeonggi"),
    ("강원", "gangwon"),
    ("충청", "chungcheong"),
    ("충북", "chungcheong"),
    ("충남", "chungcheong"),
    ("대전", "chungcheong"),
    ("세종", "chungcheong"),
    ("전라", "jeolla"),
    ("전북", "jeolla"),
    ("전남", "jeolla"),
    ("광주", "jeolla"),
    ("경상북", "gyeongbuk"),
    ("경북", "gyeongbuk"),
    ("대구", "gyeongbuk"),
    ("경상남", "gyeongnam"),
    ("경남", "gyeongnam"),
    ("부산", "gyeongnam"),
    ("울산", "gyeongnam"),
    ("제주", "jeju"),
)

# 주소가 비었을 때 쓰는 법정동 시·도 코드(lDongRegnCd). 12 = 전남광주통합특별시.
_REGN_CODE: dict[str, str] = {
    "11": "seoul",
    "28": "gyeonggi",
    "41": "gyeonggi",
    "42": "gangwon",
    "51": "gangwon",
    "30": "chungcheong",
    "36110": "chungcheong",
    "43": "chungcheong",
    "44": "chungcheong",
    "12": "jeolla",
    "29": "jeolla",
    "45": "jeolla",
    "46": "jeolla",
    "52": "jeolla",
    "27": "gyeongbuk",
    "47": "gyeongbuk",
    "26": "gyeongnam",
    "31": "gyeongnam",
    "48": "gyeongnam",
    "50": "jeju",
}


def to_iso_date(value: str | None) -> date | None:
    """TourAPI 날짜(YYYYMMDD)를 date로. 비었거나 잘못된 값은 None."""
    if not value or not re.fullmatch(r"\d{8}", value):
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def region_of(addr: str | None, regn_code: str | None = None) -> str | None:
    """주소 첫 단어(시·도)로 권역을 정하고, 주소로 못 정하면 법정동 시·도 코드를 쓴다."""
    first = (addr or "").strip().split(" ")[0]
    if first:
        for prefix, region in _ADDR_PREFIX:
            if first.startswith(prefix):
                return region
    return _REGN_CODE.get(regn_code or "")


# 도 이름은 두 글자 약칭으로. 나머지(○○특별시, ○○광역시 등)는 행정 접미사만 뗀다.
_PROVINCE_SHORT: dict[str, str] = {
    "경기도": "경기",
    "강원도": "강원",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전라북도": "전북",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주도": "제주",
    "제주특별자치도": "제주",
}
_SIDO_SUFFIX = re.compile(r"(통합특별시|특별자치시|특별시|광역시)$")


def _short_sido(word: str) -> str:
    return _PROVINCE_SHORT.get(word) or _SIDO_SUFFIX.sub("", word) or word


def _sigungu(words: list[str]) -> str | None:
    return words[1] if len(words) > 1 and words[1][-1] in "시군구" else None


def place_of(addr: str | None) -> str | None:
    """주소를 '약칭 시·도 + 시·군·구'로 (경상남도 거창군 … → 경남 거창군).

    시·군·구가 없으면(세종) 시·도만.
    """
    words = (addr or "").split()
    if not words:
        return None
    sido, sigungu = _short_sido(words[0]), _sigungu(words)
    return f"{sido} {sigungu}" if sigungu else sido


def town_of(addr: str | None) -> str | None:
    """사진이 없을 때 자리표시에 쓰는 짧은 지명 (거창군 → 거창, 세종특별자치시 → 세종)."""
    words = (addr or "").split()
    if not words:
        return None
    sigungu = _sigungu(words)
    if sigungu and len(sigungu) > 2:
        return sigungu[:-1]
    return sigungu or _short_sido(words[0])


def is_always(start: date | None, end: date | None) -> bool:
    """1년 내내(1/1~12/31) 또는 그보다 길게 열리는 행사는 상시."""
    if start is None or end is None:
        return False
    return (end - start).days >= 364


def overlaps(start: date | None, end: date | None, range_start: date, range_end: date) -> bool:
    """기간과 하루라도 겹치면 포함. 날짜가 빠진 축제는 제외."""
    if start is None or end is None:
        return False
    return start <= range_end and end >= range_start


def to_float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def clean_text(value: str | None) -> str | None:
    """TourAPI 글에 섞인 HTML 태그를 지우고 <br>은 줄바꿈으로. 빈 값은 None."""
    if not value:
        return None
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text or None


def playtime_of(value: str | None) -> str | None:
    """운영 시간을 한 줄로: 앞의 '-'·'·' 같은 기호를 떼고 줄바꿈은 ' / '로."""
    text = clean_text(value)
    if not text:
        return None
    lines = [re.sub(r"^[\s\-·•*※]+", "", line).strip() for line in text.splitlines()]
    return " / ".join(line for line in lines if line) or None


def homepage_url(value: str | None) -> str | None:
    """홈페이지 값(<a href="...">, 맨 URL)에서 http(s) 주소만 꺼낸다."""
    if not value:
        return None
    match = re.search(r"https?://[^\s\"'<>]+", value)
    return match.group(0) if match else None


# TourAPI 신분류체계(lclsSystm3) 축제/공연/행사 20종. lclsSystmCode2(lclsSystm1=EV)에서 확인.
# 거의 바뀌지 않아서 호출하지 않고 표로 둔다. 새 코드가 생기면 category가 None이 된다.
CATEGORY: dict[str, str] = {
    "EV010100": "문화관광축제",
    "EV010200": "문화예술축제",
    "EV010300": "지역특산물축제",
    "EV010400": "전통역사축제",
    "EV010500": "생태자연축제",
    "EV010600": "기타축제",
    "EV020100": "전통공연",
    "EV020200": "연극",
    "EV020300": "뮤지컬",
    "EV020400": "오페라",
    "EV020500": "무용",
    "EV020600": "클래식음악회",
    "EV020700": "대중콘서트",
    "EV020800": "영화",
    "EV020900": "기타공연",
    "EV021000": "넌버벌",
    "EV030100": "전시회",
    "EV030200": "박람회",
    "EV030300": "스포츠경기",
    "EV030400": "기타행사",
}
KINDS = ("festival", "show", "exhibit", "event")


def kind_of(code: str | None) -> str | None:
    """분류 코드 → 화면 필터 묶음: 축제 / 공연 / 전시·박람회 / 행사."""
    if not code:
        return None
    if code.startswith("EV01"):
        return "festival"
    if code.startswith("EV02"):
        return "show"
    if code in ("EV030100", "EV030200"):
        return "exhibit"
    if code.startswith("EV03"):
        return "event"
    return None


_PHONE = re.compile(r"\d{2,4}-\d{3,4}-\d{4}|\d{4}-\d{4}")


def phone_of(tel: str | None) -> str | None:
    """대표 번호 하나 ('041-730-2971, 2973' → '041-730-2971', '055-670-7491~3' → '055-670-7491')."""
    match = _PHONE.search(tel or "")
    return match.group(0) if match else None


def price_of(fee: str | None) -> str | None:
    """요금 글로 무료 여부: free(무료) / partial(무료 + 일부 유료) / paid(유료) / None(모름)."""
    if not fee:
        return None
    free = "무료" in fee
    paid = "유료" in fee or bool(re.search(r"\d[\d,]*\s*원", fee))
    if free and paid:
        return "partial"
    if free:
        return "free"
    return "paid" if paid else None


def normalize_festival(item: dict[str, Any]) -> dict[str, Any]:
    """searchFestival2 항목 하나를 앱 형태(snake_case dict)로."""
    start = to_iso_date(item.get("eventstartdate"))
    end = to_iso_date(item.get("eventenddate"))
    code = item.get("lclsSystm3")
    return {
        "id": str(item.get("contentid") or ""),
        "title": (item.get("title") or "").strip(),
        "place": place_of(item.get("addr1")),
        "place_detail": (item.get("addr2") or "").strip() or None,
        "town": town_of(item.get("addr1")),
        "region": region_of(item.get("addr1"), item.get("lDongRegnCd")),
        "category": CATEGORY.get(code or ""),
        "kind": kind_of(code),
        "start": start,
        "end": end,
        "is_always": is_always(start, end),
        "image": item.get("firstimage") or None,
        "thumb": item.get("firstimage2") or None,
        "tel": phone_of(item.get("tel")),
        "lat": to_float(item.get("mapy")),
        "lng": to_float(item.get("mapx")),
    }
