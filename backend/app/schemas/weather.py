from datetime import date

from pydantic import BaseModel


class WeatherValidateRequest(BaseModel):
    district: str
    damage_date: date
    damage_type: str
    village: str | None = None


class WeatherDetail(BaseModel):
    precipitation: float
    temperature_max: float
    temperature_min: float
    windspeed: float | None = None


class WeatherValidateResponse(BaseModel):
    verified: bool | None
    reason: str
    weather: WeatherDetail