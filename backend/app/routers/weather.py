import logging

from fastapi import APIRouter, HTTPException, status

from app.exceptions import (
    InvalidDateError,
    LocationNotFoundError,
    WeatherDataUnavailableError,
    WeatherServiceUnavailableError,
)
from app.schemas.weather import WeatherValidateRequest, WeatherValidateResponse
from app.services import weather_service

logger = logging.getLogger("fasalbima.weather.router")

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.post(
    "/validate",
    response_model=WeatherValidateResponse,
    summary="Validate a reported damage type against historical weather",
)
def validate_weather(payload: WeatherValidateRequest):
    """
    Standalone endpoint: checks whether historical weather on the reported
    damage_date supports the reported damage_type for the given district
    (and optional village). This is also called automatically after claim
    creation (see claim_service.create_claim) — this route exists
    separately so the frontend (or a future retry action) can call it
    on demand too.
    """
    try:
        return weather_service.validate_weather(
            district=payload.district,
            damage_date=payload.damage_date,
            damage_type=payload.damage_type,
            village=payload.village,
        )
    except InvalidDateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WeatherDataUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except WeatherServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc