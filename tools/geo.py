"""지오코딩 — Nominatim/OpenStreetMap (무료, 키 불필요).

버그4 수정: 목적지 좌표를 하드코딩하지 않고 동적으로 조회.
도시 이름만 있으면 어디든 좌표를 얻으므로 reusable.
Nominatim 사용 약관상 User-Agent 필수, 초당 1회 제한.
"""
import requests
import time

_last_call = 0.0

# "Fukuoka, Japan" 같은 질의는 도(prefecture) 중심(시골)을 잡아 맛집 검색이
# 0건이 되는 경우가 있다. 시/읍 단위 결과를 우선 골라 도심 좌표를 쓴다.
_CITY_TYPES = ("city", "town", "municipality", "village")


def geocode(place_name: str) -> dict:
    """도시/장소 이름 → {lat, lon}. 실패 시 success=False.

    여러 후보 중 도심(city/town)을 우선 선택해, 행정구역 중심점이 시골로
    잡히는 문제를 피한다.
    """
    global _last_call
    # 초당 1회 제한 준수
    elapsed = time.time() - _last_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place_name, "format": "json", "limit": 10,
                    "accept-language": "en", "addressdetails": 1},
            headers={"User-Agent": "travel-planner-demo/1.0"},  # 필수
            timeout=10,
        )
        _last_call = time.time()
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return {"success": False, "error": f"좌표 못 찾음: {place_name}"}
        # 도심(city/town/…) 결과가 있으면 그걸, 없으면 첫 결과(중요도 1위).
        cities = [d for d in data if d.get("addresstype") in _CITY_TYPES]
        pick = cities[0] if cities else data[0]
        return {
            "success": True,
            "lat": float(pick["lat"]),
            "lon": float(pick["lon"]),
            "display_name": pick.get("display_name", place_name),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
