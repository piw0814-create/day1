import pytest
from pydantic import ValidationError

from day1 import WeatherHourly


def test_weather_invalid_temperature_type() -> None:
    """기온에 잘못된 타입이 입력되면 ValidationError가 발생하는지 검사한다."""

    invalid_data = {
        "time": ["2026-07-15T00:00"],
        "temperature_2m": ["잘못된 기온"],
        "precipitation_probability": [50],
    }

    with pytest.raises(ValidationError):
        WeatherHourly.model_validate(invalid_data)