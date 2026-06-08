"""날씨 — Open-Meteo (완전 무료, 키 불필요)."""
import requests


def get_weather_forecast(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "auto",
            },
            timeout=10,
        )
        resp.raise_for_status()
        d = resp.json()["daily"]
        return {
            "success": True,
            "days": [
                {"date": dt, "high": hi, "low": lo, "rain_chance": rc}
                for dt, hi, lo, rc in zip(
                    d["time"], d["temperature_2m_max"],
                    d["temperature_2m_min"], d["precipitation_probability_max"],
                )
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
