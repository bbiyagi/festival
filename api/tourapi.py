"""TourAPI 4.0 (KorService2) 호출. 서비스 키는 서버 환경변수에서만 읽는다."""

import os
import time
from typing import Any

import httpx

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TIMEOUT = httpx.Timeout(10.0)
PAGE_SIZE = 1000
CACHE_TTL = 60 * 60

# ponytail: 서버리스 인스턴스별 메모리 캐시.
# 인스턴스 간 공유는 응답의 Cache-Control(s-maxage)이 맡는다. 부족하면 Vercel KV 등으로.
_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, dict[str, Any]]] = {}


class TourApiError(Exception):
    """TourAPI가 오류를 돌려줬거나 응답하지 않음."""


async def _fetch_json(operation: str, params: dict[str, str]) -> Any:
    key = os.environ.get("TOURAPI_SERVICE_KEY")
    if not key:
        raise TourApiError("TOURAPI_SERVICE_KEY가 설정되지 않았습니다")
    query = {"serviceKey": key, "MobileOS": "ETC", "MobileApp": "festival", "_type": "json"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(2):  # 시간 초과·연결 오류는 1회 재시도
            try:
                res = await client.get(f"{BASE_URL}/{operation}", params=query | params)
                break
            except httpx.TransportError as e:
                if attempt == 1:
                    raise TourApiError(f"TourAPI 응답 없음: {type(e).__name__}") from e
    try:
        return res.json()
    except ValueError as e:  # 키 오류 등은 XML로 올 때가 있다
        raise TourApiError(f"TourAPI 응답 형식 오류 (HTTP {res.status_code})") from e


def _body(data: Any) -> dict[str, Any]:
    """정상 응답이면 body를, 아니면 TourApiError. 오류 응답은 형식이 세 가지다."""
    if not isinstance(data, dict):
        raise TourApiError("TourAPI 응답 형식 오류")
    if "OpenAPI_ServiceResponse" in data:  # 인증키 오류
        header = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {})
        raise TourApiError(f"TourAPI 인증 오류: {header.get('errMsg', '알 수 없음')}")
    if "response" not in data:  # 파라미터 오류: {"resultCode": "11", "resultMsg": ...}
        raise TourApiError(f"TourAPI 오류 {data.get('resultCode')}: {data.get('resultMsg')}")
    header = data["response"].get("header", {})
    if header.get("resultCode") != "0000":
        raise TourApiError(f"TourAPI 오류 {header.get('resultCode')}: {header.get('resultMsg')}")
    return data["response"].get("body") or {}


def _items(body: dict[str, Any]) -> list[dict[str, Any]]:
    """결과가 없으면 items가 빈 문자열로 오고, 1건이면 dict로 올 수 있다."""
    items = body.get("items")
    if not items:
        return []
    item = items.get("item", [])
    return item if isinstance(item, list) else [item]


async def call(operation: str, params: dict[str, str]) -> dict[str, Any]:
    """TourAPI 한 번 호출하고 body를 돌려준다. 같은 요청은 CACHE_TTL 동안 캐시."""
    cache_key = (operation, tuple(sorted(params.items())))
    hit = _cache.get(cache_key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    body = _body(await _fetch_json(operation, params))
    _cache[cache_key] = (time.monotonic(), body)
    return body


async def call_items(operation: str, params: dict[str, str]) -> list[dict[str, Any]]:
    return _items(await call(operation, params))


async def search_festivals(start: str, end: str) -> list[dict[str, Any]]:
    """기간(YYYYMMDD)과 겹치는 축제를 마지막 페이지까지 받는다."""
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        params = {
            "eventStartDate": start,
            "eventEndDate": end,
            "numOfRows": str(PAGE_SIZE),
            "pageNo": str(page),
            "arrange": "A",
        }
        body = await call("searchFestival2", params)
        page_items = _items(body)
        items.extend(page_items)
        if not page_items or len(items) >= int(body.get("totalCount") or 0):
            return items
        page += 1
