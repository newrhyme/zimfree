import { BatteryCharging } from "lucide-react";
import type { Charger } from "../types";

export default function ChargerList({ chargers }: { chargers: Charger[] }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <BatteryCharging size={18} className="text-green-600" /> 경로 상 충전설비
      </div>
      {chargers.length === 0 ? (
        <p className="mt-2 text-sm text-gray-400">경로 상 충전설비 정보 없음</p>
      ) : (
        <ul className="mt-2 divide-y divide-gray-100">
          {chargers.map((c, i) => (
            <li key={i} className="py-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-800">{c.station}역</span>
                <span className="text-xs text-gray-500">{c.fee}</span>
              </div>
              <p className="text-xs text-gray-500">{c.detail}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
