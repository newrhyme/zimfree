import { useState } from "react";
import { AlertOctagon, Wrench } from "lucide-react";
import { api } from "../api/client";
import type { OutageResult, Station } from "../types";

// Demo presets: 다대포해수욕장 has real ALT_NONE (이동 불가) rows; the 6 escalator
// non-run stations are used as outage-demo anchors.
const DEMO_STD = [
  "다대포해수욕장",
  "양산",
  "체육공원",
  "강서구청",
  "구포",
  "만덕",
  "석대",
];

export default function OutageToggle({
  stations,
  destCode,
}: {
  stations: Station[];
  destCode: number;
}) {
  const [on, setOn] = useState(false);
  const [stationCode, setStationCode] = useState<number>(destCode);
  const [elevatorId, setElevatorId] = useState<string>("");
  const [result, setResult] = useState<OutageResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const byStd = new Map(stations.map((s) => [s.std_name, s.station_code]));
  const presets = DEMO_STD.filter((n) => byStd.has(n)).map((n) => ({
    name: n,
    code: byStd.get(n)!,
  }));

  async function simulate(code: number, elev: string) {
    setLoading(true);
    setErr(null);
    try {
      const r = await api.outage(code, elev.trim() === "" ? null : elev.trim());
      setResult(r);
    } catch (e) {
      setErr((e as Error).message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function toggle() {
    const next = !on;
    setOn(next);
    if (next) simulate(stationCode, elevatorId);
    else setResult(null);
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <Wrench size={18} className="text-orange-500" /> 엘리베이터 고장 시뮬레이션
        </div>
        <button
          onClick={toggle}
          className={`relative h-6 w-11 rounded-full transition-colors ${
            on ? "bg-orange-500" : "bg-gray-300"
          }`}
          aria-pressed={on}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
              on ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      </div>

      {on && (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap gap-2">
            <select
              value={stationCode}
              onChange={(e) => {
                const c = Number(e.target.value);
                setStationCode(c);
                simulate(c, elevatorId);
              }}
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
            >
              {presets.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name}
                </option>
              ))}
              {!presets.some((p) => p.code === destCode) && (
                <option value={destCode}>도착역</option>
              )}
            </select>
            <input
              value={elevatorId}
              onChange={(e) => setElevatorId(e.target.value)}
              onBlur={() => simulate(stationCode, elevatorId)}
              placeholder="EV 번호(전체)"
              className="w-28 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
            />
          </div>

          {loading && <p className="text-sm text-gray-400">재계산 중…</p>}
          {err && <p className="text-sm text-red-500">{err}</p>}

          {result && (
            <div
              className={`rounded-xl p-3 ${
                result.passable === false
                  ? "bg-red-50 border border-red-300"
                  : "bg-gray-50 border border-gray-200"
              }`}
            >
              {result.passable === false ? (
                <div className="flex items-center gap-2 font-bold text-red-600">
                  <AlertOctagon size={18} />
                  이동 불가 — {result.message ?? "대체경로 없음"}
                </div>
              ) : (
                <p className="text-sm font-semibold text-gray-700">
                  대체경로 있음 · 최고 복잡도 {result.worst_grade ?? "—"}
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    ({result.source === "data" ? "실데이터" : "모델 예측"})
                  </span>
                </p>
              )}
              <ul className="mt-2 space-y-2">
                {result.routes.map((rt, i) => (
                  <li key={i} className="text-xs text-gray-600">
                    <span
                      className={`mr-1 rounded px-1.5 py-0.5 font-medium ${
                        rt.passable ? "bg-gray-200 text-gray-700" : "bg-red-200 text-red-800"
                      }`}
                    >
                      {rt.grade}
                    </span>
                    {rt.depart} → {rt.arrive}: {rt.steps}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
