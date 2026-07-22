import logging
from datetime import date as date_type

import httpx

from app.config import settings
from app.exceptions import (
    InvalidDateError,
    LocationNotFoundError,
    WeatherDataUnavailableError,
    WeatherServiceUnavailableError,
)

logger = logging.getLogger("fasalbima.weather")

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_DAILY_VARS = [
    "precipitation_sum",
    "rain_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "windspeed_10m_max",
]


def _geocode(district: str, village: str | None = None) -> tuple[float, float]:
    """
    Resolves a district (optionally refined by village) to lat/lon via
    Open-Meteo's geocoding API. Tries "village, district" first when a
    village is given, since that's more precise, then falls back to the
    district alone if the combined query returns nothing.
    """
    queries = []
    if village:
        queries.append(f"{village}, {district}")
    queries.append(district)

    last_error = None
    for query in queries:
        try:
            response = httpx.get(
                _GEOCODING_URL,
                params={"name": query, "count": 1, "language": "en", "format": "json"},
                timeout=settings.weather_request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            last_error = exc
            continue

        results = data.get("results") or []
        if results:
            top = results[0]
            return top["latitude"], top["longitude"]

    if last_error is not None:
        logger.warning("Geocoding request failed for district=%s: %s", district, last_error)
        raise WeatherServiceUnavailableError("Location lookup service is unavailable.")

    raise LocationNotFoundError(district)


def _fetch_historical_weather(lat: float, lon: float, damage_date: date_type) -> dict:
    """
    Fetches a single day's historical daily aggregates for the given
    coordinates. Open-Meteo's archive API only has data up to a short delay
    behind "today", so a damage_date that's too recent will come back with
    an empty daily array — treated as WeatherDataUnavailableError.
    """
    date_str = damage_date.isoformat()
    try:
        response = httpx.get(
            _ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": date_str,
                "end_date": date_str,
                "daily": ",".join(_DAILY_VARS),
                "timezone": "auto",
            },
            timeout=settings.weather_request_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Historical weather request failed: %s", exc)
        raise WeatherServiceUnavailableError("Weather data service is unavailable.")

    daily = data.get("daily") or {}
    times = daily.get("time") or []
    if not times:
        raise WeatherDataUnavailableError(date_str)

    def _first(key: str):
        values = daily.get(key) or []
        return values[0] if values else None

    # rain_sum is Open-Meteo's closest equivalent to a "rainfall_sum" field;
    # precipitation_sum is the primary signal and is preferred when both are
    # present, since it also includes snow/showers where relevant.
    precipitation = _first("precipitation_sum")
    if precipitation is None:
        precipitation = _first("rain_sum")

    temperature_max = _first("temperature_2m_max")
    temperature_min = _first("temperature_2m_min")
    windspeed = _first("windspeed_10m_max")

    if precipitation is None or temperature_max is None or temperature_min is None:
        raise WeatherDataUnavailableError(date_str)

    return {
        "precipitation": precipitation,
        "temperature_max": temperature_max,
        "temperature_min": temperature_min,
        "windspeed": windspeed,
    }


def _evaluate(damage_type: str, weather: dict) -> tuple[bool | None, str]:
    """
    Applies the validation rule for the reported damage type against the
    fetched weather. Weather validation is corroborating evidence only —
    it never overrides the farmer-reported damage_type.
    """
    normalized = (damage_type or "").strip().lower()

    if normalized == "flood":
        if weather["precipitation"] >= 20:
            return True, "Heavy rainfall recorded on the reported date."
        return False, "Historical weather does not indicate significant rainfall."

    if normalized == "drought":
        if weather["precipitation"] < 2 and weather["temperature_max"] > 35:
            return True, "Low rainfall and high temperature recorded on the reported date."
        return False, "Historical weather does not indicate drought conditions."

    if normalized == "hailstorm":
        return None, "Historical weather cannot reliably verify hail."

    if normalized == "pest_attack":
        return None, "Weather validation is not applicable."

    return None, "Weather validation is not applicable for this damage type."


def validate_weather(district: str, damage_date, damage_type: str, village: str | None = None) -> dict:
    """
    Full weather-validation pipeline: geocode -> fetch historical weather ->
    apply the rule for the reported damage type.

    damage_date may be a date object or an ISO "YYYY-MM-DD" string.
    Raises InvalidDateError / LocationNotFoundError / WeatherDataUnavailableError
    / WeatherServiceUnavailableError on failure — callers that need claim
    creation to succeed regardless should catch these and fall back to a
    "weather service unavailable" result rather than letting them propagate.
    """
    if isinstance(damage_date, str):
        try:
            damage_date = date_type.fromisoformat(damage_date)
        except ValueError:
            raise InvalidDateError(damage_date)

    if damage_date > date_type.today():
        raise InvalidDateError(damage_date.isoformat())

    lat, lon = _geocode(district, village)
    weather = _fetch_historical_weather(lat, lon, damage_date)
    verified, reason = _evaluate(damage_type, weather)

    return {
        "verified": verified,
        "reason": reason,
        "weather": weather,
    }