"""지오코딩 — Nominatim/OpenStreetMap (무료, 키 불필요).

버그4 수정: 목적지 좌표를 하드코딩하지 않고 동적으로 조회.
도시 이름만 있으면 어디든 좌표를 얻으므로 reusable.
Nominatim 사용 약관상 User-Agent 필수, 초당 1회 제한.
"""
import requests
import time

_last_call = 0.0


def geocode(place_name: str) -> dict:
    """도시/장소 이름 → {lat, lon}. 실패 시 success=False."""
    global _last_call
    # 초당 1회 제한 준수
    elapsed = time.time() - _last_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place_name, "format": "json", "limit": 1},
            headers={"User-Agent": "travel-planner-demo/1.0"},  # 필수
            timeout=10,
        )
        _last_call = time.time()
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return {"success": False, "error": f"좌표 못 찾음: {place_name}"}
        return {
            "success": True,
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "display_name": data[0].get("display_name", place_name),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
