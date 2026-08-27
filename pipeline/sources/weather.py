"""Open-Meteo weather fetcher. No API key required."""
from __future__ import annotations

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """Returns a normalized 7-day forecast: current conditions + daily max/min/precip/wind."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,wind_gusts_10m_max",
        "forecast_days": days,
        "timezone": "auto",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    days_out = []
    for i, date in enumerate(daily.get("time", [])):
        days_out.append({
            "date": date,
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "precip_prob_pct": daily.get("precipitation_probability_max", [None])[i],
            "wind_gust_max_kmh": daily.get("wind_gusts_10m_max", [None])[i],
            "weather_code": daily["weather_code"][i],
        })

    current = data.get("current", {})
    return {
        "current": {
            "temp_c": current.get("temperature_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
        },
        "days": days_out,
    }


# WMO weather_code -> short human label (subset covering common cases)
WEATHER_CODE_LABELS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


def label_for_code(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_CODE_LABELS.get(code, "Unknown")
