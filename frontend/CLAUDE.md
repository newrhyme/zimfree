# frontend/CLAUDE.md — Vite + React 스펙

루트 `CLAUDE.md` 전역 규칙 적용. API 계약은 `backend/CLAUDE.md`가 원본이며 임의 필드 추가 금지.

## 스택·구조

Vite + React 18 + TypeScript + Tailwind CSS + react-leaflet(OSM 타일).
상태관리는 React 내장(useState/useReducer + context)만 사용 — 외부 상태 라이브러리 금지.
`vite.config.ts`에 `/api` → `http://localhost:8000` proxy.

```
frontend/src/
├── api/client.ts        # fetch 래퍼 + 타입 (backend 스펙 그대로 타이핑)
├── types.ts
├── pages/               # Planner, Result, Assistant, MapView
├── components/          # LuggageProfileForm, BoardingCard, CongestionBadge,
│                        # WarningBanner, LuggageDecisionCard, OutageToggle,
│                        # ChargerList, ChatWindow, StationSelect
└── App.tsx              # 상단 탭 네비게이션 (플래너 / 지도 / 어시스턴트)
```

## 화면 스펙

### 1. Planner (홈)
- 출발/도착역 StationSelect (GET /stations로 검색형 셀렉트, 표준역명 표시)
- 짐 프로필: 크기(S/M/L/XL 세그먼트), 개수 스테퍼, 유모차 토글
- 배터리 슬라이더(0–100%), 출발 시각 입력(기본: 현재)
- [경로 추천] 버튼 → POST /route/plan → Result로 이동

### 2. Result
- 상단: 경로 legs 타임라인 (호선 색상 배지, 환승 표시)
- **BoardingCard** (핵심): "🚪 6-1 위치에 타세요" 큰 타이포 + 엘리베이터 상세위치 + WarningBanner(연단간격 넓음/곡선 시 노란 경고)
- CongestionBadge: 레벨 4색 (여유=teal / 보통=gray / 혼잡=amber / 매우혼잡=red) + better_hours 칩("15시 출발 시 '보통'")
- battery_pct<30이면 ChargerList 섹션 노출
- LuggageDecisionCard: 3옵션 비교(휴대/보관함/짐배송), recommendation에 하이라이트, `reason`·`source_notes` 문구 그대로 노출 (데이터 근거 어필)
- **OutageToggle**: "엘리베이터 고장 시뮬레이션" 스위치 → POST /scenario/elevator-outage → 대체경로 카드로 교체 애니메이션. passable:false면 붉은 "이동 불가" 상태
- 데모 프리셋 버튼 3개 고정: ①부산역→해운대(XL×2) ②서면 금요일 18시 ③배터리 15%

### 3. Assistant
- ChatWindow: 말풍선 UI, 전송 중 typing indicator
- POST /assistant/chat. 501 응답이면 입력창 비활성 + "API 키 미설정 — 데모에서는 플래너 기능을 이용하세요" 안내
- 예시 질문 칩 3개: "해운대 가는데 캐리어 두 개야, 짐 어떻게 할까?" 등

### 4. MapView
- react-leaflet, 부산 중심 (35.16, 129.06) zoom 12
- 역 마커: stations의 lat/lng. 클릭 → GET /stations/{code}/facilities 팝업 (보관함/충전기/ATM/키오스크 유무 아이콘, 없으면 "정보 없음")

## 디자인 방향

발제 자료 톤 계승: 다크 네이비(#0d1533 계열) 헤더 + 밝은 본문, 라운드 카드, 넉넉한 여백.
모바일 우선(375px 기준) — 심사 데모는 데스크톱 브라우저의 모바일 프레임으로 시연.
lucide-react 아이콘 사용 가능. 이미지 에셋 외부 다운로드 금지(이모지·아이콘으로 대체).

## 품질 기준

- `npm run build` 무경고 통과, TypeScript strict
- API 실패 시 화면 크래시 금지 — 에러 배너로 처리
- 하드코딩 데이터 금지: 모든 수치는 API 응답에서 온다 (데모 프리셋도 요청 파라미터만 프리셋)
