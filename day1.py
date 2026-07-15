"""
3개 공공 API의 데이터를 비동기로 수집하고,
Pydantic으로 검증한 뒤 CSV와 Parquet 형식으로 저장하는 프로그램.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import httpx
import pandas as pd
from pydantic import (
    BaseModel,
    Field,
    IPvAnyAddress,
    ValidationError,
    model_validator,
)
# API 요청 주소
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)

COUNTRY_URL = "https://countries.dev/alpha/KR"
IP_URL = "http://ip-api.com/json/8.8.8.8"


class WeatherHourly(BaseModel):
    """Open-Meteo의 시간대별 날씨 데이터를 검증한다.
        검증내용: 
            세 리스트의 길이가 같은지, 
            강수 확률이 모두 0~100인지"""
    time: list[datetime]
    temperature_2m: list[float]
    precipitation_probability: list[int]

    @model_validator(mode="after")
    def validate_hourly_data(self) -> "WeatherHourly":
        """시간·기온·강수 확률의 개수와 값의 범위를 검사한다."""

        lengths = {
            len(self.time),
            len(self.temperature_2m),
            len(self.precipitation_probability),
        }

        if len(lengths) != 1:
            raise ValueError("시간, 기온, 강수 확률의 데이터 개수가 다릅니다.")

        if not all(0 <= value <= 100 for value in self.precipitation_probability):
            raise ValueError("강수 확률은 0~100 범위여야 합니다.")

        return self
    
class CountryInfo(BaseModel):
    """countries.dev의 대한민국 국가 정보를 검증한다.
        검증 내용: 
            국가명·수도·지역은 빈 문자열 불가
            국가 코드는 각각 2글자와 3글자
            인구와 인구밀도는 0 이상"""
    name: str = Field(min_length=1)
    alpha2Code: str = Field(min_length=2, max_length=2)
    alpha3Code: str = Field(min_length=3, max_length=3)
    capital: str = Field(min_length=1)
    region: str = Field(min_length=1)
    population: int = Field(ge=0)
    populationDensity: float = Field(ge=0)

class IPLocation(BaseModel):
    """ip-api의 IP 기반 지역 정보를 검증한다.
        검증 내용: 
            status는 "success"만 허용
            위도는 -90~90
            경도는 -180~180
            query는 올바른 IP 주소 형식이어야 함"""
    status: Literal["success"]
    country: str = Field(min_length=1)
    countryCode: str = Field(min_length=2, max_length=2)
    regionName: str = Field(min_length=1)
    city: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1)
    isp: str = Field(min_length=1)
    query: IPvAnyAddress

async def fetch_json(
    client: httpx.AsyncClient,
    name: str,
    url: str,
) -> dict[str, Any]:
    """API에 비동기 요청을 보내고 JSON 응답을 반환한다.
        이 함수는 각 API에 요청한 뒤: HTTP 응답 상태를 검사하고 정상일 경우 JSON을 반환하며 상태 코드가 비정상이면 예외를 발생시킨다."""
    response = await client.get(url)
    response.raise_for_status()

    print(f"{name} API 응답 정상: {response.status_code}")
    return response.json()

async def collect_all_data() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """asyncio.gather로 세 API를 동시에 호출한다."""

    timeout = httpx.Timeout(10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        weather_data, country_data, ip_data = await asyncio.gather(
            fetch_json(client, "Open-Meteo", WEATHER_URL),
            fetch_json(client, "countries.dev", COUNTRY_URL),
            fetch_json(client, "ip-api", IP_URL),
        )

    return weather_data, country_data, ip_data

def validate_data(
    weather_data: dict[str, Any],
    country_data: dict[str, Any],
    ip_data: dict[str, Any],
) -> tuple[WeatherHourly, CountryInfo, IPLocation]:
    """수집한 API 데이터를 Pydantic 모델로 검증한다.
        이 함수는 API JSON을 각 Pydantic 모델에 넣어 검증하고, 타입이나 범위가 잘못되면 ValidationError를 출력한 뒤 다시 발생시킨다."""

    try:
        weather = WeatherHourly.model_validate(weather_data.get("hourly", {}))
        country = CountryInfo.model_validate(country_data)
        ip_location = IPLocation.model_validate(ip_data)

    except ValidationError as error:
        print(f"데이터 검증 실패:\n{error}")
        raise

    print("3개 API 데이터 검증 완료")
    return weather, country, ip_location

def create_dataframes(
    weather: WeatherHourly,
    country: CountryInfo,
    ip_location: IPLocation,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """검증된 데이터를 CSV와 Parquet 저장용 표로 변환한다.
        데이터 형태 :
            날씨: 72행
            국가 정보: 1행
            IP 지역 정보: 1행"""
    # 날씨의 세 리스트를 시간대별 행으로 구성한다.
    weather_df = pd.DataFrame(
        {
            "time": weather.time,
            "temperature_2m": weather.temperature_2m,
            "precipitation_probability": weather.precipitation_probability,
        }
    ) 

    # 국가 정보와 IP 정보는 각각 한 행으로 구성한다.
    country_df = pd.DataFrame([country.model_dump(mode="json")])
    ip_df = pd.DataFrame([ip_location.model_dump(mode="json")])

    return weather_df, country_df, ip_df

def save_and_measure(dataframes: dict[str, pd.DataFrame]) -> None:
    """데이터를 CSV와 Parquet로 저장하고 읽기·쓰기 시간을 측정한다."""
    """이 함수는 weather, country, ip_location 데이터를 각각 CSV와 Parquet로 저장하고 시간을 출력한다"""

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    for name, dataframe in dataframes.items():
        csv_path = data_dir / f"{name}.csv"
        parquet_path = data_dir / f"{name}.parquet"

        # CSV 쓰기 시간을 측정한다.
        start = perf_counter()
        dataframe.to_csv(csv_path, index=False)
        csv_write_time = perf_counter() - start

        # Parquet 쓰기 시간을 측정한다.
        start = perf_counter()
        dataframe.to_parquet(parquet_path, index=False)
        parquet_write_time = perf_counter() - start

        # 저장된 파일의 읽기 시간을 각각 측정한다.
        start = perf_counter()
        pd.read_csv(csv_path)
        csv_read_time = perf_counter() - start

        start = perf_counter()
        pd.read_parquet(parquet_path)
        parquet_read_time = perf_counter() - start

        print(f"\n[{name} 저장 성능]")
        print(f"CSV 쓰기: {csv_write_time:.6f}초")
        print(f"CSV 읽기: {csv_read_time:.6f}초")
        print(f"Parquet 쓰기: {parquet_write_time:.6f}초")
        print(f"Parquet 읽기: {parquet_read_time:.6f}초")

async def main() -> None:
    """데이터 수집부터 검증·저장까지 전체 과정을 실행한다."""

    try:
        weather_data, country_data, ip_data = await collect_all_data()

        weather, country, ip_location = validate_data(
            weather_data,
            country_data,
            ip_data,
        )

        weather_df, country_df, ip_df = create_dataframes(
            weather,
            country,
            ip_location,
        )

        save_and_measure(
            {
                "weather": weather_df,
                "country": country_df,
                "ip_location": ip_df,
            }
        )

    except httpx.HTTPError as error:
        print(f"API 요청 실패: {error}")

    except ValidationError:
        print("잘못된 데이터가 있어 저장을 중단합니다.")

if __name__ == "__main__":
    asyncio.run(main())