// Types mirror backend/CLAUDE.md API contract exactly.

export interface Station {
  station_code: number;
  line: string;
  name: string;
  std_name: string;
  lat: number;
  lng: number;
  transfer_lines: string;
}

export type Size = "S" | "M" | "L" | "XL";

export interface Luggage {
  size: Size;
  count: number;
  stroller: boolean;
}

export interface PlanRequest {
  origin_code: number;
  dest_code: number;
  luggage: Luggage;
  battery_pct: number | null;
  depart_at: string | null;
}

export type Level = "여유" | "보통" | "혼잡" | "매우혼잡";

export interface Congestion {
  level: Level | null;
  pax_pred: number;
  p50: number | null;
  p80: number | null;
  p95: number | null;
  better_hours: { hour: number; level: Level }[];
  source: string;
}

export interface Leg {
  from: number;
  to: number;
  from_name: string;
  to_name: string;
  line: string;
  num_stops: number;
}

export interface Boarding {
  door_pos: string | null;
  direction?: string | null;
  elevator_id?: string | null;
  elevator_note: string | null;
  warnings: string[];
  message?: string;
}

export interface CarryOption {
  type: "carry";
  difficulty: string;
  reason: string;
}
export interface LockerOption {
  type: "locker";
  available: boolean;
  station?: string;
  detail?: string;
  fee?: string;
  reason: string;
}
export interface DeliveryOption {
  type: "delivery";
  prior: number | null;
  reason: string;
  source_note: string | null;
}
export type LuggageOption = CarryOption | LockerOption | DeliveryOption;

export interface LuggageDecision {
  recommendation: "carry" | "locker" | "delivery";
  options: LuggageOption[];
  source_notes: string[];
}

export interface Charger {
  station: string;
  detail: string;
  fee: string;
  count: string | number;
}

export interface RoutePlan {
  legs: Leg[];
  num_transfers: number;
  boarding: Boarding;
  congestion: Congestion | null;
  luggage_advice: LuggageDecision;
  charging?: Charger[];
  error?: string;
  message?: string;
}

export interface OutageRoute {
  elevator_id: string;
  depart: string;
  arrive: string;
  alt_type: string;
  grade: string;
  steps: string;
  passable: boolean;
}

export interface OutageResult {
  station_code: number;
  elevator_id: string | number | null;
  passable: boolean | null;
  worst_grade: string | null;
  routes: OutageRoute[];
  source: string;
  message?: string;
}

export interface Facilities {
  lockers: Record<string, unknown>[];
  atms: Record<string, unknown>[];
  chargers: Record<string, unknown>[];
  kiosks: Record<string, unknown>[];
  elevators_count: number;
  escalators_count: number;
}

export interface ChatResponse {
  reply: string;
  tools_used: string[];
}
