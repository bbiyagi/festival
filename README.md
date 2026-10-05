# 이번주에 뭐해?

전국 축제·행사를 이번 주 / 다음 달 일정표와 지역별로 한눈에 보는 웹앱.

- 서버: Python 3.12 + FastAPI (`api/`, 시작점 `api/index.py`) — uv로 관리
- 화면: Vue 3 + Vite + TypeScript + Pinia + Vue Router + Tailwind CSS (`src/`)
- 데이터: 한국관광공사 TourAPI 4.0 (KorService2)

## 처음 한 번

```bash
uv sync            # Python 3.12 가상환경(.venv)과 패키지 설치
npm install        # 화면 패키지 설치
cp .env.example .env   # 실제 키로 바꾸기
```

## 실행

```bash
npm run dev        # 서버(8000) + 화면(5173) 한 번에
```

- 화면: http://localhost:5173 — `/api/*` 요청은 Vite 프록시가 8000번 Python 서버로 넘긴다
- 따로 띄우기: `npm run dev:api` / `npm run dev:web`
- 상태 확인: http://localhost:5173/api/health → `{"status":"ok"}`

## API

| 요청 | 설명 |
| --- | --- |
| `GET /api/festivals?start=YYYY-MM-DD&end=YYYY-MM-DD` | 기간과 겹치는 축제 전체(최대 62일). 마지막 페이지까지 받음 |
| `GET /api/festivals/{id}` | 상세 (detailCommon2 + detailIntro2 + detailImage2 동시 호출) |

- TourAPI 오류는 `502 {"code": "TOURAPI_ERROR"}`, 결과 없음은 `200 []`, 없는 축제는 `404`
- 같은 요청은 서버 메모리에 1시간 캐시, 응답에 `Cache-Control: s-maxage=3600`
- 데이터 규칙(날짜, 권역, 상시, 기간 겹침)은 `api/festival_rules.py`. 테스트는 `tests/fixtures/`의 실제 응답 사본으로 돌고 TourAPI를 부르지 않음

## 검사

```bash
npm run test:api   # pytest
npm run lint:api   # ruff check + format --check
npm run check:web  # 화면 규칙(상태·D-day·정렬·일정표 막대) 점검
npm run build      # 타입 검사 + 프로덕션 빌드
```

## 환경변수

| 이름 | 쓰는 곳 | 비고 |
| --- | --- | --- |
| `TOURAPI_SERVICE_KEY` | 서버 전용 | 공공데이터포털 **Decoding** 키. `VITE_` 접두사 금지 |
| `VITE_NAVER_MAP_CLIENT_ID` | 브라우저 | 네이버 콘솔에 서비스 URL 등록 필수 |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` | 브라우저 | 찜하기. RLS로 자기 행만 읽고 씀 |
| `SUPABASE_SECRET_KEY` | 서버 전용 | RLS 우회 키. 알림·캘린더 예약 작업용. `VITE_` 금지 |

## Supabase (찜하기)

1. 대시보드 > SQL Editor에서 `supabase/migrations/20261005000000_favorites.sql` 실행
2. Authentication > Sign In / Providers에서 **Allow anonymous sign-ins** 켜기 (로그인 없이 기기별 찜)

## Python 패키지 추가

```bash
uv add --bounds exact <패키지>
uv export --no-dev --no-hashes --no-emit-project -o requirements.txt   # Vercel용
```

데이터 출처: 한국관광공사
