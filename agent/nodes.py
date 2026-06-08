"""에이전트 노드들 — 각 노드는 State를 받아 일부만 채워 반환.

원칙:
- 계산은 코드(날짜 교집합 등), 판단은 LLM(목적지/협상).
- 사람 수는 people 리스트 길이로만 다룬다 (하드코딩 없음).
"""
from datetime import datetime, timedelta
from collections import Counter

from agent.state import TripState
from agent.llm import ask_llm_json, ask_llm
from tools.weather import get_weather_forecast
from tools.geo import geocode
from tools.flights import search_flights
from tools.places import find_places
from tools.routing_tool import optimize_route
from tools.vibe import search_vibe_spots
from tools.reddit import search_reddit_tips


# ---------- 코드 계산 헬퍼 (LLM 아님) ----------

def _expand(date_range: str) -> set:
    start_str, end_str = date_range.split("~")
    s = datetime.strptime(start_str.strip(), "%Y-%m-%d")
    e = datetime.strptime(end_str.strip(), "%Y-%m-%d")
    return {(s + timedelta(d)).strftime("%Y-%m-%d") for d in range((e - s).days + 1)}


def _person_dates(people: list[dict]) -> dict:
    return {
        p["name"]: set().union(*[_expand(r) for r in p.get("available_dates", [])])
        for p in people if p.get("available_dates")
    }


def find_date_overlap(people: list[dict]) -> dict:
    pd = _person_dates(people)
    if not pd:
        return {"has_overlap": False}
    common = set.intersection(*pd.values())
    if common:
        days = sorted(common)
        return {"has_overlap": True, "start": days[0], "end": days[-1], "days": len(days)}
    return {"has_overlap": False}


def compute_compromise_options(people: list[dict]) -> dict:
    pd = _person_dates(people)
    names = list(pd.keys())
    leave_one_out = {}
    for excluded in names:
        others = [pd[n] for n in names if n != excluded]
        common = set.intersection(*others) if others else set()
        if common:
            leave_one_out[excluded] = sorted(common)
    counter = Counter()
    for dates in pd.values():
        counter.update(dates)
    if counter:
        mx = max(counter.values())
        best = sorted(d for d, c in counter.items() if c == mx)
    else:
        mx, best = 0, []
    return {
        "leave_one_out": leave_one_out,
        "max_attendance": {"count": mx, "total": len(names), "days": best[:7]},
    }


# ---------- 노드 ----------

def collect_constraints(state: TripState) -> dict:
    people = state["people"]
    missing = []
    for p in people:
        if not p.get("available_dates"):
            missing.append(f"{p['name']}: 날짜")
        if not p.get("budget"):
            missing.append(f"{p['name']}: 예산")
    msg = f"누락: {missing}" if missing else f"{len(people)}명 제약 수집 완료"
    return {"messages": [{"role": "system", "content": msg}]}


def coordinate_destinations(state: TripState) -> dict:
    people = state["people"]
    overlap = find_date_overlap(people)

    if not overlap["has_overlap"]:
        # 날짜 안 겹침 → 후보 안 만들고 라우터에 단서만 남김
        return {"date_overlap": overlap}

    summary = "\n".join(
        f"- {p['name']}: 예산 {p.get('budget', 0):,}원, 피로도 {p.get('energy_level','?')}, "
        f"희망 {p.get('wishes', [])}, 출발 {p.get('departure_city','?')}"
        for p in people
    )
    prompt = f"""다음 {len(people)}명을 위한 목적지 후보 3곳을 제안해.
여행 가능: {overlap['start']} ~ {overlap['end']} ({overlap['days']}일)
여행자:
{summary}

규칙: 최저 예산자도 감당 가능 / 피로도 low 있으면 빡센 일정 회피 /
모두의 희망 최소 하나씩 충족.
JSON 배열로만 답해 (설명·코드펜스 금지):
[{{"destination":"도시명","why":"이유","tradeoffs":"단점"}}]"""

    candidates = ask_llm_json(prompt, fallback=[])
    return {
        "date_overlap": overlap,
        "chosen_dates": f"{overlap['start']} ~ {overlap['end']}",
        "destination_candidates": candidates,
    }


def negotiate(state: TripState) -> dict:
    people = state["people"]
    attempts = state.get("negotiate_attempts", 0)
    opts = compute_compromise_options(people)

    prefs = "\n".join(
        f"- {p['name']}: 피로도 {p.get('energy_level','?')}, 예산 {p.get('budget',0):,}원, "
        f"희망 {p.get('wishes',[])}, 양보불가 {p.get('hard_constraints',[])}"
        for p in people
    )
    prompt = f"""여행 날짜가 전원 겹치지 않아 타협이 필요해.

[코드가 계산한 사실 — 이 안에서만 제안할 것, 날짜 지어내기 금지]
- 한 명 빼면 겹치는 날: {opts['leave_one_out']}
- 가장 많이 겹치는 날: {opts['max_attendance']}

[선호]
{prefs}

사람이 고를 타협안 2~3개를 제안해. 각 안: 누가 무엇을 양보 / 왜 합리적 / 단점."""

    proposal = ask_llm(prompt)
    return {
        "messages": [{"role": "assistant", "content": proposal}],
        "negotiate_attempts": attempts + 1,
        "awaiting_human": True,
    }


def ask_human(state: TripState) -> dict:
    # 협상 3회 실패 → 사람에게 위임 (데모에선 메시지만 남김)
    return {
        "messages": [{"role": "system",
                      "content": "날짜 조율 자동 해결 실패. 직접 조율이 필요합니다."}],
        "awaiting_human": True,
    }


def choose_destination(state: TripState) -> dict:
    """버그3 수정: 후보 중 하나를 확정하고 좌표까지 채운다.

    데모에선 첫 후보를 자동 선택. 실제로는 여기서 interrupt 로
    사람에게 후보를 보여주고 고르게 하는 게 맞다 (Human-in-the-loop).
    """
    candidates = state.get("destination_candidates", [])
    if not candidates:
        return {"messages": [{"role": "system", "content": "후보 없음"}]}

    chosen = candidates[0]["destination"]
    geo = geocode(chosen)  # 버그4 수정: 좌표 동적 조회
    coords = {"lat": geo["lat"], "lon": geo["lon"]} if geo.get("success") else {}
    return {
        "chosen_destination": chosen,
        "chosen_coords": coords,
        "messages": [{"role": "system", "content": f"목적지 확정: {chosen}"}],
    }


def make_todos(state: TripState) -> dict:
    dest = state.get("chosen_destination", "목적지")
    dates = state.get("chosen_dates", "")
    return {"todos": [
        {"task": "항공권 검색 (각자 출발지)", "category": "flight", "status": "pending"},
        {"task": "숙소 리서치/비교", "category": "stay", "status": "pending"},
        {"task": f"{dates} 날씨 확인", "category": "weather", "status": "pending"},
        {"task": "맛집·카페·관광·감성명소 리스트업", "category": "activity", "status": "pending"},
    ]}


def research_full(state: TripState) -> dict:
    dest = state.get("chosen_destination", "")
    coords = state.get("chosen_coords", {})
    people = state["people"]
    dates = state.get("chosen_dates", "")
    research = {}

    # 날씨 (좌표 있을 때)
    if coords and dates:
        start, end = [x.strip() for x in dates.split("~")]
        research["weather"] = get_weather_forecast(coords["lat"], coords["lon"], start, end)

    # 항공 — 사람마다 출발지 다름 (N명 무관 루프)
    start_date = dates.split("~")[0].strip() if dates else ""
    research["flights"] = {
        p["name"]: search_flights(p.get("departure_city", ""), dest, start_date,
                                  max_price=p.get("budget", 0) // 3)
        for p in people
    }

    # 맛집·카페·관광 — 희망사항을 카테고리로 자동 변환
    if coords:
        lat, lon = coords["lat"], coords["lon"]
        all_wishes = {w for p in people for w in p.get("wishes", [])}
        if "맛집" in all_wishes:
            research["restaurants"] = find_places(lat, lon, "restaurant")
        if "카페" in all_wishes:
            research["cafes"] = find_places(lat, lon, "cafe")
        research["attractions"] = find_places(lat, lon, "attraction")

        # 동선 최적화 — 관광지 결과를 입력으로 (도구가 도구를 먹음)
        attractions = research.get("attractions", {}).get("places", [])
        if len(attractions) >= 2:
            research["day_route"] = optimize_route(attractions[:8])

    # 감성 + 로컬 후기 (다양한 매체 섞기)
    if dest:
        research["vibe"] = search_vibe_spots(dest)
        research["reddit"] = search_reddit_tips(dest)

    return {"research_results": research}
