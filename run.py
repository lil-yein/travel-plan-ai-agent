"""실행 진입점.

  python run.py

ANTHROPIC_API_KEY 만 있으면 핵심 흐름이 돈다.
나머지 키는 없으면 해당 도구가 자동 스킵/mock 처리.
"""
import json
from dotenv import load_dotenv

load_dotenv()  # .env 읽기 (반드시 그래프 import 전)

from agent.graph import build_travel_agent

# 친구 수 제한 없음 — 리스트에 넣는 만큼 처리됨
SAMPLE_PEOPLE = [
    {"name": "Yein", "available_dates": ["2026-10-03 ~ 2026-10-12"],
     "budget": 1500000, "energy_level": "medium",
     "wishes": ["맛집", "온천", "카페"], "departure_city": "Seoul",
     "hard_constraints": []},
    {"name": "친구A", "available_dates": ["2026-10-05 ~ 2026-10-15"],
     "budget": 1000000, "energy_level": "high",
     "wishes": ["액티비티"], "departure_city": "Busan",
     "hard_constraints": []},
    {"name": "친구B", "available_dates": ["2026-10-02 ~ 2026-10-10"],
     "budget": 1200000, "energy_level": "low",
     "wishes": ["휴식", "카페"], "departure_city": "Seoul",
     "hard_constraints": []},
]


def main():
    agent = build_travel_agent()
    initial = {"people": SAMPLE_PEOPLE, "todos": [], "messages": [],
               "negotiate_attempts": 0}

    # recursion_limit: 협상 루프 등 폭주 방지 (LangGraph 기본 25)
    final = agent.invoke(initial, {"recursion_limit": 25})

    print("\n=== 결과 ===")
    print("확정 날짜:", final.get("chosen_dates", "(미정)"))
    print("확정 목적지:", final.get("chosen_destination", "(미정)"))

    print("\n후보지:")
    for c in final.get("destination_candidates", []):
        print(f"  - {c.get('destination')}: {c.get('why', '')}")

    print("\n투두:")
    for t in final.get("todos", []):
        print(f"  [{t['status']}] {t['task']}")

    print("\n리서치 키:", list(final.get("research_results", {}).keys()))

    print("\n로그:")
    for m in final.get("messages", []):
        print(f"  ({m['role']}) {m['content'][:80]}")


if __name__ == "__main__":
    main()
