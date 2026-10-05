from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import tourapi
from api.index import app
from tests.conftest import load

client = TestClient(app)
WEEK = {"start": "2026-10-05", "end": "2026-10-11"}


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_festivals(fake_tourapi: dict[str, Any]) -> None:
    res = client.get("/api/festivals", params=WEEK)
    assert res.status_code == 200
    assert "s-maxage" in res.headers["cache-control"]
    by_id = {f["id"]: f for f in res.json()}
    assert len(by_id) == 7
    gokseong = by_id["1322668"]
    keys = ("title", "place", "town", "region", "start", "end", "isAlways")
    assert {k: gokseong[k] for k in keys} == {
        "title": "곡성심청어린이대축제",
        "place": "전남광주 곡성군",
        "town": "곡성",
        "region": "jeolla",
        "start": "2026-10-08",
        "end": "2026-10-11",
        "isAlways": False,
    }
    assert gokseong["image"].startswith("https://")
    assert isinstance(gokseong["lat"], float) and isinstance(gokseong["lng"], float)
    assert gokseong["kind"] == "festival" and gokseong["category"]
    assert gokseong["thumb"].startswith("https://") and gokseong["tel"]
    assert by_id["3481597"]["isAlways"] is True  # 2022-11-01 ~ 2026-12-31
    assert by_id["4116376"]["region"] == "gyeongnam"  # 주소가 "부산"으로 시작
    assert by_id["1849007"]["region"] == "chungcheong"  # 세종
    op, params = fake_tourapi["calls"][0]
    assert op == "searchFestival2"
    assert (params["eventStartDate"], params["eventEndDate"]) == ("20261005", "20261011")


def test_festivals_cached(fake_tourapi: dict[str, Any]) -> None:
    client.get("/api/festivals", params=WEEK)
    client.get("/api/festivals", params=WEEK)
    assert len(fake_tourapi["calls"]) == 1


def test_festivals_pages_until_total(
    fake_tourapi: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tourapi, "PAGE_SIZE", 3)
    items = load("search_week.json")["response"]["body"]["items"]["item"]

    async def paged(operation: str, params: dict[str, str]) -> Any:
        fake_tourapi["calls"].append((operation, params))
        page, size = int(params["pageNo"]), int(params["numOfRows"])
        body = {"items": {"item": items[(page - 1) * size : page * size]}, "totalCount": 7}
        return {"response": {"header": {"resultCode": "0000"}, "body": body}}

    monkeypatch.setattr(tourapi, "_fetch_json", paged)
    res = client.get("/api/festivals", params=WEEK)
    assert len(res.json()) == 7
    assert [c[1]["pageNo"] for c in fake_tourapi["calls"]] == ["1", "2", "3"]


def test_festivals_empty(fake_tourapi: dict[str, Any]) -> None:
    fake_tourapi["responses"]["searchFestival2"] = load("empty.json")
    res = client.get("/api/festivals", params=WEEK)
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.parametrize("fixture", ["error_key.json", "error_param.json"])
def test_festivals_tourapi_error(fake_tourapi: dict[str, Any], fixture: str) -> None:
    fake_tourapi["responses"]["searchFestival2"] = load(fixture)
    res = client.get("/api/festivals", params=WEEK)
    assert res.status_code == 502
    assert res.json()["code"] == "TOURAPI_ERROR"
    assert "cache-control" not in res.headers


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-10-11", "end": "2026-10-05"},
        {"start": "2026-01-01", "end": "2026-12-31"},
        {"start": "20261005", "end": "2026-10-11"},
    ],
)
def test_festivals_bad_range(fake_tourapi: dict[str, Any], params: dict[str, str]) -> None:
    assert client.get("/api/festivals", params=params).status_code in (400, 422)
    assert fake_tourapi["calls"] == []


def test_detail(fake_tourapi: dict[str, Any]) -> None:
    res = client.get("/api/festivals/506376")
    assert res.status_code == 200
    d = res.json()
    assert d["title"] == "강경젓갈축제"
    assert (d["start"], d["end"]) == ("2026-10-15", "2026-10-18")  # detailIntro2에서 옴
    assert d["region"] == "chungcheong"
    assert d["address"] == "충청남도 논산시 강경읍 황산리 198 강경 금강둔치 일원"
    assert len(d["images"]) == 3
    assert d["homepage"] == "https://www.nonsan.go.kr/ggfestival/"
    assert d["host"] == "논산시"
    assert d["fee"].startswith("입장료 무료")
    assert d["price"] == "partial"  # 입장료 무료, 일부 체험 유료
    assert d["tel"] == "041-730-2971"
    assert d["placeDetail"] == "강경 금강둔치 일원"
    assert (d["category"], d["kind"]) == ("지역특산물축제", "festival")
    assert d["ageLimit"] is None
    ops = {c[0] for c in fake_tourapi["calls"]}
    assert ops == {"detailCommon2", "detailIntro2", "detailImage2"}


def test_intro(fake_tourapi: dict[str, Any]) -> None:
    res = client.get("/api/festivals/intro", params={"ids": "506376,506376,abc"})
    assert res.status_code == 200
    # 중복·숫자 아닌 id는 빼고, 같은 축제는 한 번만 부른다
    assert res.json() == [{"id": "506376", "playtime": "10:00~22:00", "price": "partial"}]
    assert [c[0] for c in fake_tourapi["calls"]] == ["detailIntro2"]


def test_intro_limits_and_partial_failure(
    fake_tourapi: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def flaky(operation: str, params: dict[str, str]) -> Any:
        fake_tourapi["calls"].append((operation, params))
        if params["contentId"] == "2":
            return load("error_param.json")
        return load("detail_intro.json")

    monkeypatch.setattr(tourapi, "_fetch_json", flaky)
    ids = ",".join(str(i) for i in range(1, 41))
    body = client.get("/api/festivals/intro", params={"ids": ids}).json()
    assert len(fake_tourapi["calls"]) == 30  # 최대 30개
    assert "2" not in {r["id"] for r in body} and len(body) == 29  # 하나 실패해도 나머지는 온다


def test_link(fake_tourapi: dict[str, Any]) -> None:
    res = client.get("/api/festivals/506376/link")
    assert res.status_code == 200
    assert res.json() == {"url": "https://www.nonsan.go.kr/ggfestival/"}
    assert [c[0] for c in fake_tourapi["calls"]] == ["detailCommon2"]  # 상세 3종 중 1개만


def test_link_missing(fake_tourapi: dict[str, Any]) -> None:
    fake_tourapi["responses"]["detailCommon2"] = load("empty.json")
    assert client.get("/api/festivals/1/link").json() == {"url": None}
    assert client.get("/api/festivals/abc/link").status_code == 404


def test_detail_not_found(fake_tourapi: dict[str, Any]) -> None:
    for op in ("detailCommon2", "detailIntro2", "detailImage2"):
        fake_tourapi["responses"][op] = load("empty.json")
    assert client.get("/api/festivals/1").status_code == 404
    assert client.get("/api/festivals/abc").status_code == 404
