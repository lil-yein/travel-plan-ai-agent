"""TripState — 모든 노드가 읽고 쓰는 '서류 가방'.

설계 원칙:
- 사람 수는 데이터(people 리스트)에 두고, 코드는 개수를 모른다.
- Annotated[..., add] 필드는 덮어쓰지 않고 누적된다.
"""
from typing import TypedDict, Annotated, Optional
from operator import add


class PersonConstraints(TypedDict, total=False):
    name: str
    available_dates: list[str]   # ["2026-10-03 ~ 2026-10-12", ...]
    budget: int                  # KRW
    energy_level: str            # "high" | "medium" | "low"
    wishes: list[str]            # ["맛집", "온천", "카페", ...]
    departure_city: str          # 각자 다를 수 있음
    hard_constraints: list[str]  # 절대 양보 불가


class TripState(TypedDict, total=False):
    # 입력
    people: list[PersonConstraints]

    # coordinate 단계
    date_overlap: dict
    chosen_dates: str
    destination_candidates: list[dict]

    # choose 단계 (버그3 수정: 후보 중 하나 확정하는 필드)
    chosen_destination: str
    chosen_coords: dict          # {"lat":..., "lon":...}

    # 진행 산출물 (버그6 수정: 이름 research_results 로 통일)
    todos: Annotated[list[dict], add]
    research_results: dict

    # 루프 안전장치 (버그5)
    negotiate_attempts: int

    # 사람 개입
    awaiting_human: bool

    # 로그
    messages: Annotated[list, add]
