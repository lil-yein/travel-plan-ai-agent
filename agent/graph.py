"""그래프 조립 — 노드 등록 + 엣지(직선/조건/루프) 연결 후 컴파일."""
from langgraph.graph import StateGraph, START, END

from agent.state import TripState
from agent.routing import route_after_coordinate
from agent.nodes import (
    collect_constraints, coordinate_destinations, negotiate, ask_human,
    choose_destination, make_todos, research_full,
)


def build_travel_agent():
    g = StateGraph(TripState)

    g.add_node("collect", collect_constraints)
    g.add_node("coordinate", coordinate_destinations)
    g.add_node("negotiate", negotiate)
    g.add_node("ask_human", ask_human)
    g.add_node("choose", choose_destination)
    g.add_node("make_todos", make_todos)
    g.add_node("research", research_full)

    g.add_edge(START, "collect")
    g.add_edge("collect", "coordinate")

    # 조건 분기: coordinate 후 날짜 겹침 여부로 갈라짐
    g.add_conditional_edges(
        "coordinate", route_after_coordinate,
        {"choose": "choose", "negotiate": "negotiate", "ask_human": "ask_human"},
    )

    g.add_edge("negotiate", "coordinate")  # 루프: 협상 → 재조율
    g.add_edge("ask_human", END)           # 비상구: 사람에게 위임 후 종료

    g.add_edge("choose", "make_todos")
    g.add_edge("make_todos", "research")
    g.add_edge("research", END)

    return g.compile()
