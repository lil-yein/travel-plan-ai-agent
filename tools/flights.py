"""항공권 — 키 없으면 mock 데이터 + 검색 링크로 동작 ($0).

실제 가격이 필요하면 FLIGHT_API_KEY 설정 후 _search_real 구현.
예약 자체는 절대 하지 않음 — booking/search URL 만 제공, 결제는 사람이.
"""
import os
import urllib.parse


def search_flights(origin: str, destination: str, date: str, max_price: int = None) -> dict:
    api_key = os.getenv("FLIGHT_API_KEY")
    if not api_key:
        # mock + 실제 검색 링크 (Google Flights)
        q = urllib.parse.quote(f"flights from {origin} to {destination} on {date}")
        return {
            "success": True,
            "mock": True,
            "search_url": f"https://www.google.com/search?q={q}",
            "flights": [{
                "airline": "(예시)",
                "price": 250000,
                "departure": f"{date} 09:30",
                "duration": "2h 20m",
                "stops": 0,
                "note": "FLIGHT_API_KEY 설정 시 실시간 가격으로 대체",
            }],
        }
    return _search_real(api_key, origin, destination, date, max_price)


def _search_real(api_key, origin, destination, date, max_price):
    # TODO: 실제 항공 API 연결 지점. 인터페이스는 위와 동일하게 유지.
    return {"success": False, "error": "실제 항공 API 미구현 (mock 사용 권장)"}
