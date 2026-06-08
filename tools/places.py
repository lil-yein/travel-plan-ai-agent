"""맛집·카페·관광 — OSM Overpass (완전 무료, 키 불필요)."""
import requests

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
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query, timeout=30,
        )
        resp.raise_for_status()
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
