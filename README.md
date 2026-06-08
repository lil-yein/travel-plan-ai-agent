# 여행 플랜 에이전트 (LangGraph)

친구 N명의 제약조건(날짜·예산·피로도·희망·출발지)을 조율해 목적지·일정·투두를
만들고, 날씨·항공·맛집·카페·관광·동선·감성 명소를 리서치하는 에이전트.

> 결제/예약은 절대 자동으로 하지 않습니다. 검색·비교·링크 준비까지만 하고,
> 실제 결제 버튼은 사람이 누릅니다.

## 빠른 시작

```bash
pip install -r requirements.txt
cp .env.example .env        # ANTHROPIC_API_KEY 만 채우면 핵심 흐름이 돕니다
python run.py
```

## 웹으로 공개하기 (Railway 백엔드 + Vercel 프론트)

이 에이전트는 리서치 단계에서 외부 API를 여러 번 순차 호출하므로 한 번 실행에
수십 초~몇 분이 걸릴 수 있다. Vercel 서버리스 함수는 요청 타임아웃(Hobby 10초)이
있어 풀 실행이 끊길 수 있으므로, **에이전트는 타임아웃이 없는 상시 서버(Railway 등)에**
두고 프론트만 Vercel에 두는 구성을 권장한다.

### 1) 백엔드 — Railway에 배포

`server.py` 가 LangGraph 그래프를 HTTP API로 감싼다.

- `POST /plan` — `people` 리스트를 받아 에이전트를 돌리고 결과 JSON 반환
- `GET /health` — 헬스체크

```bash
# 로컬에서 먼저 돌려보기
pip install -r requirements.txt
cp .env.example .env        # ANTHROPIC_API_KEY 채우기
uvicorn server:app --reload --port 8000
# 다른 터미널에서:
curl -X POST localhost:8000/plan -H 'content-type: application/json' \
  -d '{"people":[{"name":"Yein","available_dates":["2026-10-03 ~ 2026-10-12"],"budget":1500000,"energy_level":"medium","wishes":["맛집"],"departure_city":"Seoul"}]}'
```

Railway 배포: [railway.app](https://railway.app) → New Project → Deploy from GitHub repo →
이 레포 선택. Railway가 `Procfile`(`uvicorn server:app ...`)을 자동 인식한다.
대시보드 **Variables** 에 `ANTHROPIC_API_KEY`(필수)와 선택 키들을 넣고,
`ALLOWED_ORIGINS=https://your-app.vercel.app` 로 CORS를 프론트 도메인으로 좁힌다.
배포되면 `https://...up.railway.app` 공개 URL이 나온다.

> Render/Fly.io도 동일하게 `Procfile`을 쓰면 된다. Render 무료 티어는 15분 유휴 시
> 슬립(다음 요청 콜드스타트 ~30초)되는 점만 다르다.

### 2) 프론트 — Vercel

Next.js(또는 정적 페이지)에서 입력 폼을 만들고 위 URL로 `fetch`:

```js
const res = await fetch("https://your-backend.up.railway.app/plan", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ people }),
});
const plan = await res.json();
```

Vercel 환경변수에 백엔드 URL을 넣고, 실행 중에는 로딩 상태를 보여주면 된다
(상시 서버라 오래 걸려도 끊기지 않는다).

## 비용 — 거의 다 무료

| 도구 | API | 비용 |
|---|---|---|
| 날씨 | Open-Meteo | 무료 (키 불필요) |
| 좌표 | Nominatim/OSM | 무료 (키 불필요) |
| 맛집·카페·관광 | Overpass/OSM | 무료 (키 불필요) |
| 동선 최적화 | OpenRouteService | 무료 2,000회/일 |
| 감성 영상 | YouTube Data API | 무료 1만 유닛/일 |
| 감성 웹 | Tavily | 무료 1,000회/월 |
| 로컬 후기 | Reddit | 개인용 무료 |
| LLM | Anthropic | 유료 (사용량 과금, 1회 실행 수 센트) |
| 항공권 | (mock) | 무료 — 키 없으면 검색링크 제공 |

키 없는 선택적 도구는 자동으로 스킵/mock 되므로, 하나씩 켜며 확장하면 됩니다.

## 구조

```
agent/
  state.py    TripState — 모든 노드가 공유하는 '서류 가방'
  llm.py      모델 호출 + 안전한 JSON 파싱
  nodes.py    collect → coordinate → (choose | negotiate | ask_human) → make_todos → research
  routing.py  조건 분기 라우터
  graph.py    그래프 조립 + 컴파일
tools/        weather, geo, places, routing_tool, flights, vibe, reddit
run.py        샘플 입력으로 CLI 실행
server.py     FastAPI — 같은 그래프를 HTTP API(/plan)로 노출 (웹 배포용)
```

## 흐름

1. **collect** — N명 제약 검증
2. **coordinate** — 날짜 교집합 *코드로* 계산, 겹치면 LLM이 목적지 후보 3개
3. 분기 — 겹치면 `choose`, 충돌이면 `negotiate`(3회 실패 시 `ask_human`)
4. **choose** — 후보 확정 + 좌표 조회 (데모는 첫 후보 자동)
5. **make_todos** — 투두 생성
6. **research** — 도구들이 날씨·항공·맛집·동선·감성 리서치

## 핵심 설계 원칙

- 사람 수는 데이터(리스트)에 — 코드는 개수를 모른다 (N명 reusable).
- 계산은 코드(날짜·교집합), 판단은 LLM(목적지·협상).
- 도구는 절대 예외로 죽지 않는다 — 실패도 `{"success": False}` 데이터로.
- 돈 쓰는 행동은 자동화하지 않는다 — 링크까지만, 결제는 사람.

## 입력 방식 확장

지금은 `run.py`에 직접 입력(A). `collect` 노드에 `interrupt`를 붙이면
빠진 정보를 에이전트가 되묻는 대화형(B)으로, 더 나아가 폼 수집(C)으로 확장 가능.
권장 순서: A로 검증 → B → C.
