"""날씨 — Open-Meteo (완전 무료, 키 불필요).

Open-Meteo 예보(forecast)는 약 16일 앞까지만 된다. 그보다 먼 미래
(예: 내년 가을 여행)는 forecast가 400을 내므로, '작년 같은 날짜'의
실측(historical archive)을 받아 예년 날씨로 보여준다.
"""
from datetime import datetime

import requests

_FORECAST = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def _parse_daily(d: dict, rain_key: str) -> list:
    return [
        {"date": dt, "high": hi, "low": lo, "rain_chance": rc}
        for dt, hi, lo, rc in zip(
            d["time"], d["temperature_2m_max"],
            d["temperature_2m_min"], d[rain_key],
        )
    ]


def _shift_year(date_str: str, years: int) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    try:
        return dt.replace(year=dt.year - years).strftime("%Y-%m-%d")
    except ValueError:  # 2/29 같은 날짜 보정
        return dt.replace(year=dt.year - years, day=28).strftime("%Y-%m-%d")


def _too_far_ahead(start_date: str, limit_days: int = 14) -> bool:
    try:
        return (datetime.strptime(start_date, "%Y-%m-%d") - datetime.utcnow()).days > limit_days
    except ValueError:
        return False


def _forecast(lat, lon, start, end) -> dict:
    resp = requests.get(_FORECAST, params={
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "start_date": start, "end_date": end, "timezone": "auto",
    }, timeout=10)
    resp.raise_for_status()
    return {"success": True, "source": "forecast",
            "days": _parse_daily(resp.json()["daily"], "precipitation_probability_max")}


def _archive(lat, lon, start, end) -> dict:
    """작년 같은 날짜의 실측 → 예년 참고용."""
    a_start, a_end = _shift_year(start, 1), _shift_year(end, 1)
    resp = requests.get(_ARCHIVE, params={
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "start_date": a_start, "end_date": a_end, "timezone": "auto",
    }, timeout=15)
    resp.raise_for_status()
    return {
        "success": True, "source": "historical",
        "note": f"먼 미래라 실시간 예보 불가 → 작년 동기({a_start}~{a_end}) 실측 (예년 참고용)",
        "days": _parse_daily(resp.json()["daily"], "precipitation_sum"),
    }


def get_weather_forecast(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    # 16일 이상 먼 미래면 예보가 안 되므로 바로 archive 사용
    if _too_far_ahead(start_date):
        try:
            return _archive(lat, lon, start_date, end_date)
        except Exception as e:
            return {"success": False, "error": f"archive 실패: {e}"}
    # 가까운 미래는 예보 시도, 실패하면 archive 폴백
    try:
        return _forecast(lat, lon, start_date, end_date)
    except Exception:
        try:
            return _archive(lat, lon, start_date, end_date)
        except Exception as e:
            return {"success": False, "error": str(e)}
