import { useState } from "react";
import { BatteryCharging, Search } from "lucide-react";
import StationSelect from "../components/StationSelect";
import LuggageProfileForm from "../components/LuggageProfileForm";
import { api } from "../api/client";
import type { Luggage, PlanRequest, RoutePlan, Station } from "../types";

interface Preset {
  label: string;
  origin: number;
  dest: number;
  luggage: Luggage;
  battery: number;
  departAt: string;
}

// Presets only preset request params (no hardcoded result data).
const PRESETS: Preset[] = [
  {
    label: "① 부산역→해운대 (XL×2)",
    origin: 113,
    dest: 203,
    luggage: { size: "XL", count: 2, stroller: false },
    battery: 80,
    departAt: "2026-07-08T14:00",
  },
  {
    label: "② 서면 금요일 18시",
    origin: 119,
    dest: 203,
    luggage: { size: "M", count: 1, stroller: false },
    battery: 80,
    departAt: "2026-01-02T18:00",
  },
  {
    label: "③ 배터리 15%",
    origin: 113,
    dest: 203,
    luggage: { size: "L", count: 1, stroller: false },
    battery: 15,
    departAt: "2026-07-08T14:00",
  },
];

function toLocalInput(iso: string) {
  return iso.slice(0, 16);
}

export default function Planner({
  stations,
  onResult,
}: {
  stations: Station[];
  onResult: (plan: RoutePlan, req: PlanRequest) => void;
}) {
  const [origin, setOrigin] = useState<number | null>(113);
  const [dest, setDest] = useState<number | null>(203);
  const [luggage, setLuggage] = useState<Luggage>({ size: "XL", count: 2, stroller: false });
  const [battery, setBattery] = useState(80);
  const [departAt, setDepartAt] = useState("2026-07-08T14:00");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function applyPreset(p: Preset) {
    setOrigin(p.origin);
    setDest(p.dest);
    setLuggage(p.luggage);
    setBattery(p.battery);
    setDepartAt(p.departAt);
  }

  async function submit() {
    if (origin == null || dest == null) {
      setErr("출발역과 도착역을 선택하세요");
      return;
    }
    setLoading(true);
    setErr(null);
    const req: PlanRequest = {
      origin_code: origin,
      dest_code: dest,
      luggage,
      battery_pct: battery,
      depart_at: departAt,
    };
    try {
      const plan = await api.routePlan(req);
      onResult(plan, req);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => applyPreset(p)}
            className="rounded-full border border-navy-700 px-3 py-1.5 text-xs font-medium text-navy-800 hover:bg-navy-900/5"
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="space-y-3 rounded-2xl bg-white p-4 shadow-sm">
        <StationSelect stations={stations} value={origin} onChange={setOrigin} label="출발역" />
        <StationSelect stations={stations} value={dest} onChange={setDest} label="도착역" />
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <LuggageProfileForm luggage={luggage} onChange={setLuggage} />
      </div>

      <div className="space-y-3 rounded-2xl bg-white p-4 shadow-sm">
        <div>
          <label className="mb-1 flex items-center justify-between text-xs font-medium text-gray-500">
            <span className="flex items-center gap-1">
              <BatteryCharging size={14} /> 배터리
            </span>
            <span className={battery < 30 ? "font-bold text-red-500" : ""}>{battery}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={battery}
            onChange={(e) => setBattery(Number(e.target.value))}
            className="w-full accent-navy-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">출발 시각</label>
          <input
            type="datetime-local"
            value={toLocalInput(departAt)}
            onChange={(e) => setDepartAt(e.target.value)}
            className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {err && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-600">{err}</div>
      )}

      <button
        onClick={submit}
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-navy-900 py-3.5 font-bold text-white disabled:opacity-60"
      >
        <Search size={18} /> {loading ? "경로 계산 중…" : "경로 추천"}
      </button>
    </div>
  );
}
