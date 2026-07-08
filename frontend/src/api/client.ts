import type {
  ChatResponse,
  Congestion,
  Facilities,
  Level,
  Luggage,
  OutageResult,
  PlanRequest,
  RoutePlan,
  Station,
} from "../types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const api = {
  stations: () => req<Station[]>("/stations"),
  facilities: (code: number) => req<Facilities>(`/stations/${code}/facilities`),
  congestion: (code: number, date: string, hour: number, io: string) =>
    req<Congestion>(
      `/congestion?station_code=${code}&date=${date}&hour=${hour}&io_type=${io}`
    ),
  routePlan: (body: PlanRequest) =>
    req<RoutePlan>("/route/plan", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  luggageDecision: (origin_code: number, dest_code: number, luggage: Luggage) =>
    req("/luggage/decision", {
      method: "POST",
      body: JSON.stringify({ origin_code, dest_code, luggage }),
    }),
  outage: (station_code: number, elevator_id: string | number | null) =>
    req<OutageResult>("/scenario/elevator-outage", {
      method: "POST",
      body: JSON.stringify({ station_code, elevator_id }),
    }),
  assistantStatus: () =>
    req<{ enabled: boolean; model: string }>("/assistant/status"),
  chat: (message: string) =>
    req<ChatResponse>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};

export const LEVEL_META: Record<
  Level,
  { bg: string; text: string; label: string }
> = {
  여유: { bg: "bg-teal-100", text: "text-teal-800", label: "여유" },
  보통: { bg: "bg-gray-200", text: "text-gray-700", label: "보통" },
  혼잡: { bg: "bg-amber-100", text: "text-amber-800", label: "혼잡" },
  매우혼잡: { bg: "bg-red-100", text: "text-red-700", label: "매우혼잡" },
};

export const LINE_COLOR: Record<string, string> = {
  "1호선": "#f06a00",
  "2호선": "#00a84d",
  "3호선": "#bb8c00",
  "4호선": "#2c7cd8",
};
