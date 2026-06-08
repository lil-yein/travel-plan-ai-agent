"""조건 분기 라우터 — State만 읽고 다음 노드 '이름'을 반환 (일은 안 함)."""
from agent.state import TripState


def route_after_coordinate(state: TripState) -> str:
    overlap = state.get("date_overlap", {})
    attempts = state.get("negotiate_attempts", 0)

    if overlap.get("has_overlap"):
        return "choose"          # 날짜 OK → 목적지 확정으로
    if attempts >= 3:            # 버그5: 3회 협상 실패 → 사람에게
        return "ask_human"
    return "negotiate"           # 충돌 → 협상
