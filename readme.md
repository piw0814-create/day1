# 비동기 API 데이터 수집 실습

## 1. 프로젝트 개요

`asyncio`와 `httpx`를 이용해 서로 다른 3개의 API를 동시에 호출하고,  
수집한 데이터를 Pydantic v2 모델로 검증한 뒤 CSV와 Parquet 형식으로 저장하는 프로젝트입니다.

저장 과정에서는 CSV와 Parquet의 읽기·쓰기 시간을 측정하여 성능을 비교합니다.

---

## 2. 사용 API

### Open-Meteo

서울의 향후 3일간 시간대별 기온과 강수 확률을 조회합니다.

- 시간
- 기온
- 강수 확률

### countries.dev

국가 코드 `KR`을 이용해 대한민국 정보를 조회합니다.

- 국가명
- 국가 코드
- 수도
- 지역
- 인구
- 인구밀도

### ip-api

IP 주소 `8.8.8.8`의 지역 정보를 조회합니다.

- 국가
- 지역
- 도시
- 위도와 경도
- 시간대
- ISP
- IP 주소

---

## 3. 주요 기능

- Python 가상환경과 `requirements.txt`를 이용한 패키지 관리
- `httpx.AsyncClient`를 이용한 비동기 HTTP 요청
- `asyncio.gather()`를 이용한 3개 API 동시 수집
- Pydantic v2를 이용한 타입 및 범위 검증
- 검증 오류 발생 시 `ValidationError` 예외 처리
- 수집 데이터를 pandas DataFrame으로 변환
- CSV와 Parquet 형식으로 데이터 저장
- CSV와 Parquet 읽기·쓰기 시간 측정
- pytest를 이용한 스키마 검증 테스트
- Ruff를 이용한 코드 스타일 검사

---

## 4. 프로젝트 구조

```text
day1/
├── data/
│   ├── country.csv
│   ├── country.parquet
│   ├── ip_location.csv
│   ├── ip_location.parquet
│   ├── weather.csv
│   └── weather.parquet
├── tests/
│   └── test_day1.py
├── .gitignore
├── day1.py
├── pytest.ini
├── readme.md
└── requirements.txt
```

---

## 5. 설치 방법

### 가상환경 생성

```bash
python3 -m venv .venv
```

### 가상환경 활성화

macOS 또는 Linux:

```bash
source .venv/bin/activate
```

### 패키지 설치

```bash
python -m pip install -r requirements.txt
```

---

## 6. 실행 방법

```bash
python day1.py
```

실행하면 다음 과정이 순서대로 진행됩니다.

1. 3개 API 동시 호출
2. HTTP 응답 상태 확인
3. Pydantic 데이터 검증
4. DataFrame 변환
5. CSV와 Parquet 저장
6. 읽기·쓰기 시간 출력

---

## 7. Pydantic 검증 항목

### 날씨 데이터

- 시간, 기온, 강수 확률 리스트 길이가 같은지 검사
- 강수 확률이 0에서 100 사이인지 검사
- 시간과 기온 데이터 타입 검사

### 국가 데이터

- 국가명, 수도, 지역이 빈 문자열이 아닌지 검사
- 국가 코드 길이 검사
- 인구와 인구밀도가 0 이상인지 검사

### IP 지역 데이터

- API 상태가 `success`인지 검사
- 위도가 -90에서 90 사이인지 검사
- 경도가 -180에서 180 사이인지 검사
- IP 주소 형식이 올바른지 검사

---

## 8. 성능 측정 결과

아래 결과는 한 번의 실행에서 측정한 값이며, 실행 환경에 따라 달라질 수 있습니다.

| 데이터 | 형식 | 쓰기 시간 | 읽기 시간 |
|---|---|---:|---:|
| weather | CSV | 0.011445초 | 0.001264초 |
| weather | Parquet | 0.043794초 | 0.034369초 |
| country | CSV | 0.000556초 | 0.000353초 |
| country | Parquet | 0.000836초 | 0.000895초 |
| ip_location | CSV | 0.000324초 | 0.000309초 |
| ip_location | Parquet | 0.000576초 | 0.000678초 |

현재 데이터 크기가 작고, 첫 Parquet 실행 시 `pyarrow` 초기화 시간이 포함될 수 있으므로 측정 결과만으로 저장 형식의 절대적인 성능 우열을 판단하기는 어렵습니다.

---

## 9. 테스트

Pydantic 모델에 잘못된 기온 타입을 입력했을 때 `ValidationError`가 발생하는지 검사합니다.

```bash
python -m pytest
```

실행 결과:

```text
1 passed
```

---

## 10. 코드 스타일 검사

```bash
```

실행 결과:

```text
All checks passed!
```

---

## 11. 사용 기술

- Python 3.11
- asyncio
- httpx
- Pydantic v2
- pandas
- PyArrow
- pytest
- Ruff