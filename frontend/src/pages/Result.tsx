import { ArrowLeft, ArrowRight } from "lucide-react";
import { LINE_COLOR } from "../api/client";
import BoardingCard from "../components/BoardingCard";
import CongestionBadge from "../components/CongestionBadge";
import ChargerList from "../components/ChargerList";
import LuggageDecisionCard from "../components/LuggageDecisionCard";
import OutageToggle from "../components/OutageToggle";
import type { PlanRequest, RoutePlan, Station } from "../types";

export default function Result({
  plan,
  req,
  stations,
  onBack,
}: {
  plan: RoutePlan;
  req: PlanRequest;
  stations: Station[];
  onBack: () => void;
}) {
  return (
    <div className="space-y-4 p-4">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500">
        <ArrowLeft size={16} /> 다시 검색
      </button>

      {/* legs timeline */}
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <div className="mb-2 text-sm font-semibold text-gray-700">
          경로 · 환승 {plan.num_transfers}회
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {plan.legs.map((leg, i) => (
            <div key={i} className="flex items-center gap-1.5">
              {i > 0 && <ArrowRight size={14} className="text-gray-300" />}
              <span
                className="rounded-lg px-2 py-1 text-xs font-medium text-white"
                style={{ backgroundColor: LINE_COLOR[leg.line] ?? "#555" }}
              >
                {leg.from_name} → {leg.to_name}
                <span className="ml-1 opacity-80">({leg.num_stops}정거장)</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <BoardingCard boarding={plan.boarding} />
      <CongestionBadge congestion={plan.congestion} />

      {req.battery_pct != null && req.battery_pct < 30 && plan.charging && (
        <ChargerList chargers={plan.charging} />
      )}

      <LuggageDecisionCard decision={plan.luggage_advice} />
      <OutageToggle stations={stations} destCode={req.dest_code} />
    </div>
  );
}
