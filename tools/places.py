"""맛집·카페·관광 — OSM Overpass (완전 무료, 키 불필요).

Overpass는 User-Agent 없는 요청을 406으로 거절하고, 서버가 붐비면 504를
낸다. 그래서 (1) User-Agent를 붙이고 (2) 미러를 돌며 재시도한다.
"""
import requests

# 필수: User-Agent 없으면 406 Not Acceptable
_HEADERS = {"User-Agent": "travel-planner-demo/1.0"}
# 1순위 실패 시 다음 미러로 폴백
_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

_FILTERS = {
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "attraction": "tourism=attraction",
}


def find_places(lat: float, lon: float, category: str, radius_m: int = 3000) -> dict:
    osm_filter = _FILTERS.get(category, "amenity=restaurant")
    query = f"""
    [out:json][timeout:25];
    node[{osm_filter}](around:{radius_m},{lat},{lon});
    out body 30;
    """
    last_err = "no endpoint tried"
    try:
        resp = None
        for url in _ENDPOINTS:
            try:
                r = requests.post(url, data=query, headers=_HEADERS, timeout=30)
                r.raise_for_status()
                resp = r
                break
            except Exception as e:  # 미러 하나 실패 → 다음 미러로
                last_err = str(e)
        if resp is None:
            return {"success": False, "error": last_err}
        elements = resp.json().get("elements", [])
        places = [
            {
                "name": e["tags"].get("name", ""),
                "lat": e["lat"],
                "lon": e["lon"],
                "cuisine": e["tags"].get("cuisine", ""),
            }
            for e in elements if e.get("tags", {}).get("name")
        ]
        return {"success": True, "category": category, "places": places[:20]}
    except Exception as e:
        return {"success": False, "error": str(e)}
