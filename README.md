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
run.py        샘플 입력으로 실행
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
