import json
from pathlib import Path
from typing import Any

import pytest

from api import tourapi

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def fake_tourapi(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """실제 TourAPI 대신 저장해 둔 응답을 돌려준다. responses[operation]을 바꿔 오류를 흉내 낸다."""
    tourapi._cache.clear()
    responses: dict[str, Any] = {
        "searchFestival2": load("search_week.json"),
        "detailCommon2": load("detail_common.json"),
        "detailIntro2": load("detail_intro.json"),
        "detailImage2": load("detail_image.json"),
    }
    calls: list[tuple[str, dict[str, str]]] = []

    async def fake_fetch(operation: str, params: dict[str, str]) -> Any:
        calls.append((operation, params))
        return responses[operation]

    monkeypatch.setattr(tourapi, "_fetch_json", fake_fetch)
    return {"responses": responses, "calls": calls}
