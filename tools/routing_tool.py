"""동선 최적화 — OpenRouteService (무료 2,000회/일).

키 없으면 success=False 로 우아하게 스킵 (그래프는 계속 진행).
ORS는 [경도, 위도] 순서 주의.
"""
import os
import requests


def optimize_route(places: list[dict]) -> dict:
    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        return {"success": False, "skipped": True, "error": "ORS_API_KEY 없음 (선택)"}
    if len(places) < 2:
        return {"success": False, "error": "장소 2곳 이상 필요"}

    jobs = [{"id": i, "location": [p["lon"], p["lat"]]} for i, p in enumerate(places)]
    vehicles = [{
        "id": 1,
        "start": [places[0]["lon"], places[0]["lat"]],
        "end": [places[0]["lon"], places[0]["lat"]],
    }]
    try:
        resp = requests.post(
            "https://api.openrouteservice.org/optimization",
            json={"jobs": jobs, "vehicles": vehicles},
            headers={"Authorization": api_key},
            timeout=20,
        )
        resp.raise_for_status()
        steps = resp.json()["routes"][0]["steps"]
        ordered = [places[s["job"]]["name"] for s in steps if s["type"] == "job"]
        return {"success": True, "optimal_order": ordered}
    except Exception as e:
        return {"success": False, "error": str(e)}
