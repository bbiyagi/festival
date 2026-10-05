import asyncio
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from api import festival_rules as rules
from api import tourapi

app = FastAPI(title="이번주에 뭐해? API")

MAX_RANGE_DAYS = 62
CACHE_CONTROL = "public, s-maxage=3600, stale-while-revalidate=86400"


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Festival(CamelModel):
    id: str
    title: str
    place: str | None
    place_detail: str | None  # 세부 장소 (예: 강경 금강둔치 일원)
    town: str | None
    region: str | None
    category: str | None  # 지역특산물축제, 전시회 …
    kind: Literal["festival", "show", "exhibit", "event"] | None
    start: date | None
    end: date | None
    is_always: bool
    image: str | None
    thumb: str | None  # 작은 사진 (모바일 썸네일·지도 카드)
    tel: str | None  # 대표 번호 하나
    lat: float | None
    lng: float | None


class FestivalDetail(Festival):
    address: str | None
    images: list[str]
    overview: str | None
    playtime: str | None
    event_place: str | None
    fee: str | None
    price: Literal["free", "partial", "paid"] | None
    host: str | None
    host_tel: str | None
    organizer: str | None
    organizer_tel: str | None
    tel_name: str | None
    homepage: str | None
    program: str | None
    age_limit: str | None
    booking_place: str | None


@app.exception_handler(tourapi.TourApiError)
async def tourapi_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc), "code": "TOURAPI_ERROR"}, status_code=502)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/festivals", response_model=list[Festival])
async def festivals(start: date, end: date, response: Response) -> list[dict]:
    if end < start:
        raise HTTPException(400, "end는 start보다 빠를 수 없습니다")
    if (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(400, f"기간은 최대 {MAX_RANGE_DAYS}일입니다")
    items = await tourapi.search_festivals(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    result = [rules.normalize_festival(item) for item in items]
    response.headers["Cache-Control"] = CACHE_CONTROL
    return [f for f in result if rules.overlaps(f["start"], f["end"], start, end)]


class FestivalIntro(CamelModel):
    id: str
    playtime: str | None  # 운영 시간 (예: 10:00~20:00)
    price: Literal["free", "partial", "paid"] | None


MAX_INTRO_IDS = 30
# ponytail: TourAPI에 몰리지 않게 동시 6개.
# 사용자가 늘면 매일 미리 받아 저장(Supabase)으로 바꾼다.
_intro_slots = asyncio.Semaphore(6)


@app.get("/api/festivals/intro", response_model=list[FestivalIntro])
async def festival_intro(ids: str, response: Response) -> list[dict]:
    """목록 카드의 운영 시간·무료 여부.

    화면에 보이는 카드만 묶어서 요청한다 (축제당 detailIntro2 1회, 최대 30개).
    """
    wanted = [i for i in dict.fromkeys(ids.split(",")) if i.isdigit()][:MAX_INTRO_IDS]

    async def one(festival_id: str) -> dict:
        async with _intro_slots:
            items = await tourapi.call_items(
                "detailIntro2", {"contentId": festival_id, "contentTypeId": "15"}
            )
        raw = items[0] if items else {}
        return {
            "id": festival_id,
            "playtime": rules.playtime_of(raw.get("playtime")),
            "price": rules.price_of(raw.get("usetimefestival")),
        }

    results = await asyncio.gather(*(one(i) for i in wanted), return_exceptions=True)
    response.headers["Cache-Control"] = CACHE_CONTROL
    # 한 축제가 실패해도 나머지는 보여 준다
    return [r for r in results if isinstance(r, dict)]


class FestivalLink(CamelModel):
    url: str | None


@app.get("/api/festivals/{festival_id}/link", response_model=FestivalLink)
async def festival_link(festival_id: str, response: Response) -> dict:
    """카드를 누르면 열 홈페이지. 목록 API에는 없어서 detailCommon2만 한 번 부른다."""
    if not festival_id.isdigit():
        raise HTTPException(404, "축제를 찾을 수 없습니다")
    common = await tourapi.call_items("detailCommon2", {"contentId": festival_id})
    response.headers["Cache-Control"] = CACHE_CONTROL
    return {"url": rules.homepage_url(common[0].get("homepage")) if common else None}


@app.get("/api/festivals/{festival_id}", response_model=FestivalDetail)
async def festival_detail(festival_id: str, response: Response) -> dict:
    if not festival_id.isdigit():
        raise HTTPException(404, "축제를 찾을 수 없습니다")
    common, intro, images = await asyncio.gather(
        tourapi.call_items("detailCommon2", {"contentId": festival_id}),
        tourapi.call_items("detailIntro2", {"contentId": festival_id, "contentTypeId": "15"}),
        tourapi.call_items(
            "detailImage2", {"contentId": festival_id, "imageYN": "Y", "numOfRows": "30"}
        ),
    )
    if not common:
        raise HTTPException(404, "축제를 찾을 수 없습니다")
    raw = common[0] | (intro[0] if intro else {})
    base = rules.normalize_festival(raw)
    image_urls = [i["originimgurl"] for i in images if i.get("originimgurl")]
    if not image_urls and base["image"]:
        image_urls = [base["image"]]
    address = " ".join(filter(None, [raw.get("addr1"), raw.get("addr2")])) or None
    t = rules.clean_text
    response.headers["Cache-Control"] = CACHE_CONTROL
    return base | {
        "address": address,
        "images": image_urls,
        "overview": t(raw.get("overview")),
        "playtime": rules.playtime_of(raw.get("playtime")),
        "event_place": t(raw.get("eventplace")),
        "fee": t(raw.get("usetimefestival")),
        "price": rules.price_of(raw.get("usetimefestival")),
        "host": t(raw.get("sponsor1")),
        "host_tel": t(raw.get("sponsor1tel")),
        "organizer": t(raw.get("sponsor2")),
        "organizer_tel": t(raw.get("sponsor2tel")),
        "tel_name": t(raw.get("telname")),
        "homepage": rules.homepage_url(raw.get("homepage") or raw.get("eventhomepage")),
        "program": t(raw.get("program")),
        "age_limit": t(raw.get("agelimit")),
        "booking_place": t(raw.get("bookingplace")),
    }
