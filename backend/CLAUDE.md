# backend/CLAUDE.md — FastAPI + ML 스펙

루트 `CLAUDE.md`의 데이터 계약을 전제로 한다. 이 문서와 충돌하면 루트가 우선.

## 디렉토리

```
backend/
├── pyproject.toml           # fastapi, uvicorn, pandas, lightgbm, scikit-learn, anthropic, pytest, httpx
├── app/
│   ├── main.py              # FastAPI 앱, CORS(로컬 5173 허용), 라우터 등록
│   ├── schema.py            # 한글 컬럼 → snake_case 매핑 단일 정의 + pydantic 모델
│   ├── db.py                # SQLite 커넥션 (data/processed/app.db)
│   ├── routers/             # stations, congestion, route, luggage, scenario, assistant
│   └── services/            # 비즈니스 로직 (라우터는 얇게)
├── scripts/
│   ├── preprocess.py        # raw 13종 → app.db (멱등, 재실행 안전)
│   ├── train_congestion.py
│   └── train_route_difficulty.py
├── models/                  # *.txt (LightGBM), metrics.json
└── tests/
```

## 1) 전처리 파이프라인 (scripts/preprocess.py)

산출 테이블 (app.db):

- `stations`: station_code(PK), line, name, std_name, sub_name, lat, lng, transfer_lines
- `ridership_hourly`(long format): station_code, date, dow, io_type(board/alight), hour(1..24), pax
  — wide 24컬럼을 melt. `합계` 컬럼은 검증용으로만 쓰고 저장하지 않음
- `congestion_stats`: station_code, dow, hour, io_type, mean_pax, p50, p80, p95
  — 혼잡 레벨 산정 기준: 해당 역·시간 자체 분포 대비 (여유<p50 / 보통<p80 / 혼잡<p95 / 매우혼잡≥p95)
- `elevators`, `escalators`: 원본 + `door_pos`(정규식 `(\d{1,2}-\d)` 첫 매치, 없으면 NULL) + `direction_hint`(상세위치에서 "○○행"/"○○역 방향" 추출, 없으면 NULL)
- `platform_gap`: station_code, updown, direction(승강장위치에서 "행" 앞 추출), door_pos, gap(좁음/보통/넓음), curve(직선/곡선)
- `boarding_positions`: station_code, direction, recommended_door_pos, elevator_id, warning_gap, warning_curve
  — 생성 로직: platform_gap의 (역, direction)별로, 같은 역 엘리베이터 중 door_pos가 있고 direction_hint가 해당 direction과 일치(부분 문자열)하는 것을 우선, 없으면 door_pos 있는 아무 엘리베이터. 해당 door_pos의 gap/curve를 warning으로 부착
- `lockers`, `atms`, `chargers`, `kiosks`: 표준역명→station_code 매핑해 저장 (환승역이면 해당 역 모든 station_code에 복제하지 말고 대표 1개 — std_name 기준 최소 역번호 — 에만 연결)
- `alt_routes`: 03_3 원본 + snake_case (모델 학습·조회 공용)
- `flow_priors`: direction(delivery/pickup), hub, region, ratio — 05_* 3종 파싱 (루트 문서의 skiprows 규칙 준수)
- `region_anchor`: region, anchor_station_code (루트 문서의 권역→대표역 상수)

멱등성: 실행 시 app.db를 새로 빌드(DROP&CREATE). 완료 후 행수 검증 assert (stations==114, alt_routes==932 등) 실패 시 비정상 종료.

## 2) 모델

### 혼잡도 예측 — LightGBM Regressor
- target: `pax` (시간대 승객수)
- features: station_code(categorical), line, dow(categorical), month, hour, io_type, is_holiday(2025 대한민국 공휴일 하드코딩 리스트 허용 — 데이터 발명이 아니라 달력 상식)
- split: 1~10월 train / 11~12월 valid. metric: MAE. `models/metrics.json`에 기록
- 서빙: 예측값을 congestion_stats의 분위수와 비교해 level(여유/보통/혼잡/매우혼잡) 산출. 모델 파일 없으면 congestion_stats 룩업으로 폴백 (서비스는 죽지 않는다)

### 대체경로 난이도 — LightGBM Classifier
- target: `경로복잡도 등급` 4클래스 (단순/보통/복잡/이동 불가) — 클래스 불균형 있으므로 `class_weight='balanced'`
- features: line, is_terminal, is_transfer, platform_type, depart_zone/floor, arrive_zone/floor, direction
- 학습 데이터에서 `경로복잡도 점수`·`학습라벨`·`대체경로유형`은 leakage이므로 feature에서 제외
- split: StratifiedKFold(5) CV로 macro-F1 기록. 전체로 재학습 후 저장
- 서빙: (station, elevator, 출발→도착) 질의 시 alt_routes 실데이터가 있으면 그것을 우선 반환(ground truth), 없는 조합만 모델 예측 — 응답에 `source: "data" | "model"` 명시

## 3) API 스펙 (모두 `/api` prefix, JSON)

`GET /stations` → `[{station_code, line, name, std_name, lat, lng, transfer_lines}]`

`GET /stations/{code}/facilities` → `{lockers:[...], atms:[...], chargers:[...], kiosks:[...], elevators_count, escalators_count}` (없는 항목은 빈 배열)

`GET /congestion?station_code&date&hour&io_type` →
`{level, pax_pred, p50, p80, p95, better_hours: [{hour, level}]}` — better_hours는 ±3시간 내 level이 낮아지는 슬롯 최대 3개

`POST /route/plan`
```json
req: {"origin_code":119, "dest_code":203, "luggage":{"size":"XL","count":2,"stroller":false},
      "battery_pct":15, "depart_at":"2026-07-08T14:00"}
res: {"legs":[{"from":..,"to":..,"line":..}],
      "boarding":{"door_pos":"6-1","elevator_note":"...","warnings":["곡선구간 주의"]},
      "congestion":{...},
      "charging":[{"station":"서면","detail":"(B1) …","fee":"1,600원(1시간당)"}]  // battery_pct<30일 때만
      ,"luggage_advice":{...}}  // 아래 /luggage/decision과 동일 구조
```
경로 탐색은 노선 그래프(역 인접 리스트를 stations의 역번호 순서 + 환승노선명으로 구성)를 BFS. 소요시간 계산은 MVP 범위 밖 — 정차역 수만 반환.

`POST /luggage/decision`
```json
req: {"origin_code":119,"dest_code":203,"luggage":{"size":"XL","count":2}}
res: {"recommendation":"delivery",
      "options":[
        {"type":"carry","difficulty":"복잡","reason":"환승 1회 + 요청 시간대 혼잡"},
        {"type":"locker","available":true,"station":"서면","price":"특대 6,000원/3h"},
        {"type":"delivery","prior":0.64,"reason":"부산역→해운대·기장은 짐배송 이용자의 64%가 선택한 구간"}],
      "source_notes":["flow_priors: 부산역→해운대·기장 0.64"]}
```
스코어링은 규칙 기반: carry는 난이도모델+혼잡, locker는 크기 재고 매칭(커버 밖이면 available:false), delivery는 flow prior. 근거 문자열을 반드시 채운다(심사 어필 포인트).

`POST /scenario/elevator-outage` → `{"station_code":..,"elevator_id":..}` 입력, alt_routes/모델에서 대체경로+등급 반환. `대체경로유형=ALT_NONE`이면 `{"passable":false, "message":"고장 시 이 구간은 이동 불가"}`

`POST /assistant/chat` — Anthropic Messages API tool-use 루프.
- system: 서비스 소개 + "도구 결과에 없는 사실을 지어내지 말 것"
- tools: get_route_plan, get_congestion, get_boarding_position, get_station_facilities, decide_luggage, simulate_elevator_outage (위 서비스 함수 재사용)
- 모델: `claude-sonnet-4-6`, max_tokens 1024, 루프 최대 5회
- `ANTHROPIC_API_KEY` 미설정 시 501 + `{"detail":"assistant disabled"}` — 프론트는 이를 감지해 채팅 탭에 안내 표시

## 4) 테스트 (pytest)

- preprocess 후 행수/스키마 assert (stations 114, alt_routes 932, boarding_positions ≥ 90역)
- `/congestion`: 서면(119) 금요일 18시 → level이 '혼잡' 이상
- `/route/plan`: 부산역→해운대 기본 시나리오가 boarding.door_pos를 반환
- `/scenario/elevator-outage`: ALT_NONE 케이스가 passable:false
- 모델 metrics.json 존재 + macro-F1 > 0.6 (미달 시 실패 대신 경고 출력)
