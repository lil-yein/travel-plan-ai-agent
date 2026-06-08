"""감성 명소 — 유튜브(영상) + 웹검색(인스타/틱톡 간접).

소셜 API 직접 접근은 2026년 기준 막혀있어 합법적 대체 소스 사용.
각 소스는 키 없으면 스킵 — 있는 만큼만 결과를 모은다.
"""
import os
import requests


def search_vibe_spots(destination: str, vibe_keyword: str = "감성 카페 뷰맛집") -> dict:
    sources = {}

    yt_key = os.getenv("YOUTUBE_API_KEY")
    if yt_key:
        sources["youtube"] = _youtube(yt_key, destination, vibe_keyword)

    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        sources["web"] = _tavily(tavily_key, destination, vibe_keyword)

    if not sources:
        return {"success": False, "skipped": True,
                "error": "YOUTUBE_API_KEY / TAVILY_API_KEY 둘 다 없음 (선택)"}
    return {"success": True, "destination": destination,
            "vibe": vibe_keyword, "sources": sources}


def _youtube(key, destination, vibe):
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": f"{destination} {vibe}",
                    "type": "video", "maxResults": 5, "order": "relevance", "key": key},
            timeout=10,
        )
        r.raise_for_status()
        return [
            {"title": i["snippet"]["title"],
             "channel": i["snippet"]["channelTitle"],
             "url": f"https://youtube.com/watch?v={i['id']['videoId']}"}
            for i in r.json().get("items", []) if i["id"].get("videoId")
        ]
    except Exception as e:
        return {"error": str(e)}


def _tavily(key, destination, vibe):
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": f"{destination} 인스타 감성 {vibe} 추천",
                  "max_results": 5},
            timeout=15,
        )
        r.raise_for_status()
        return [
            {"title": x["title"], "url": x["url"], "snippet": x["content"][:200]}
            for x in r.json().get("results", [])
        ]
    except Exception as e:
        return {"error": str(e)}
