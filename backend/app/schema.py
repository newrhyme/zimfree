"""Single source of truth for Korean-column -> snake_case mapping and paths.

Per root CLAUDE.md rule #3: raw CSVs are read with their original Korean
headers; every mapping from Korean to English snake_case lives here and only
here. Processed tables and the API use the snake_case names below.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "app.db"
MODELS_DIR = BACKEND_DIR / "models"

RAW_ENCODING = "utf-8-sig"  # all raw files are UTF-8 with BOM

# ---------------------------------------------------------------------------
# Raw file names
# ---------------------------------------------------------------------------
F_STATION = "01_station_master_revised.csv"
F_RIDERSHIP = "02_ridership_2025_revised.csv"
F_ELEVATOR = "03_1_elevator_revised.csv"
F_ESCALATOR = "03_2_escalator_revised.csv"
F_ALT_ROUTE = "03_3_elevator_alternative_route_revised.csv"
F_PLATFORM = "03_4_platform_gap_curve_revised.csv"
F_LOCKER = "04_1_locker_sample_revised.csv"
F_ATM = "04_2_atm_revised.csv"
F_CHARGER = "04_3_phone_charger_revised.csv"
F_KIOSK = "04_4_accessibility_kiosk_revised.csv"
F_FLOW_SUMMARY = "05_flow_direction_summary_revised.csv"
F_FLOW_HUB_TO_LODGING = "05_flow_hub_to_lodging_revised.csv"
F_FLOW_LODGING_TO_HUB = "05_flow_lodging_to_hub_revised.csv"

# ---------------------------------------------------------------------------
# Korean -> snake_case column maps (only columns we keep)
# ---------------------------------------------------------------------------
STATION_COLS = {
    "역번호": "station_code",
    "호선명": "line",
    "역명": "name",
    "표준역명": "std_name",
    "부역명": "sub_name",
    "위도": "lat",
    "경도": "lng",
    "환승노선명": "transfer_lines",
}

RIDERSHIP_META_COLS = {
    "역번호": "station_code",
    "표준역명": "std_name",
    "년월일": "date",
    "요일": "dow",
    "구분": "io_type_kr",
}

# io_type normalization
IO_TYPE_MAP = {"승차": "board", "하차": "alight"}

# hourly wide columns "01시-02시" .. "24시-01시" -> hour int 1..24
def hour_col(hour: int) -> str:
    end = 1 if hour == 24 else hour + 1
    return f"{hour:02d}시-{end:02d}시"


HOUR_COLS = [hour_col(h) for h in range(1, 25)]

ELEVATOR_COLS = {
    "호선명": "line",
    "표준역명": "std_name",
    "엘리베이터 관리번호": "elevator_id",
    "근접 출입구번호": "near_exit",
    "상세위치": "detail",
    "정원(인원수)": "capacity",
    "승강기 상태": "status",
}

ESCALATOR_COLS = {
    "호선명": "line",
    "표준역명": "std_name",
    "에스컬레이터 관리번호": "escalator_id",
    "운행방향": "run_direction",
    "시작층(상세위치)": "detail_start",
    "종료층(상세위치)": "detail_end",
    "승강기 상태": "status",
}

ALT_ROUTE_COLS = {
    "호선명": "line",
    "역번호": "station_code",
    "표준역명": "std_name",
    "종착역 여부": "is_terminal",
    "환승역 여부": "is_transfer",
    "승강장 유형": "platform_type",
    "엘리베이터 내부 관리번호": "elevator_inner_id",
    "엘리베이터 고유번호": "elevator_uid",
    "출발층": "depart_floor",
    "출발 구분": "depart_zone",
    "출발층위": "depart_level",
    "도착층": "arrive_floor",
    "도착 구분": "arrive_zone",
    "도착층위": "arrive_level",
    "이동방향": "direction",
    "단계별 대체 경로": "alt_steps",
    "경로 이용 가능 여부": "passable_raw",
    "경로복잡도 점수": "complexity_score",
    "경로복잡도 등급": "complexity_grade",
    "학습라벨": "train_label",
    "대체경로유형": "alt_type",
}

PLATFORM_COLS = {
    "호선": "line",
    "역번호": "station_code",
    "표준역명": "std_name",
    "상하선": "updown",
    "승강장위치": "platform_pos",
    "연단간격": "gap",
    "승강장선형": "curve",
}

LOCKER_COLS = {
    "표준역명": "std_name",
    "상세위치": "detail",
    "소형(개수)": "size_s",
    "중형(개수)": "size_m",
    "대형(개수)": "size_l",
    "특대형(개수)": "size_xl",
    "이용요금": "fee",
    "운영사": "operator",
}

ATM_COLS = {
    "표준역명": "std_name",
    "설치역층": "floor",
    "상세위치": "detail",
    "금융기관명": "bank",
    "이용가능시간": "hours",
}

CHARGER_COLS = {
    "표준역명": "std_name",
    "설치역층": "floor",
    "상세위치": "detail",
    "충전설비수": "count",
    "이용요금": "fee",
}

KIOSK_COLS = {
    "표준역명": "std_name",
    "상세위치": "detail",
    "음성 서비스 여부": "voice",
    "점자 서비스 여부": "braille",
    "시각 서비스 여부": "visual",
}

# ---------------------------------------------------------------------------
# Region -> anchor station (root CLAUDE.md constant). std_name used to resolve
# to a station_code at preprocess time.
# ---------------------------------------------------------------------------
REGION_ANCHORS = {
    "해운대·기장": "해운대",
    "광안리": "광안",
    "서면·부산진구": "서면",
    "원도심(동구·중구)": "중앙",
}

# Flow hub display names as they appear in the raw dump (row order matters)
FLOW_HUBS = ["부산역", "김해국제공항", "부산항 국제여객터미널"]
FLOW_REGIONS = ["해운대·기장", "광안리", "서면·부산진구", "원도심(동구·중구)", "기타"]

# 2025 South Korea public holidays (calendar common-knowledge, not invented data)
KR_HOLIDAYS_2025 = {
    "2025-01-01",
    "2025-01-28", "2025-01-29", "2025-01-30",  # Seollal
    "2025-03-01", "2025-03-03",  # Independence Movement Day + substitute
    "2025-05-05", "2025-05-06",  # Children's Day / Buddha's Birthday + substitute
    "2025-06-06",  # Memorial Day
    "2025-08-15",  # Liberation Day
    "2025-10-03",  # National Foundation Day
    "2025-10-06", "2025-10-07", "2025-10-08",  # Chuseok
    "2025-10-09",  # Hangeul Day
    "2025-12-25",  # Christmas
}
