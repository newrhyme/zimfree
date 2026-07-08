import { LEVEL_META } from "../api/client";
import type { Congestion } from "../types";

export default function CongestionBadge({ congestion }: { congestion: Congestion | null }) {
  if (!congestion || !congestion.level) {
    return (
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <p className="text-sm text-gray-500">혼잡도 정보 없음</p>
      </div>
    );
  }
  const meta = LEVEL_META[congestion.level];
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">출발역 혼잡도</span>
        <span className={`rounded-full px-3 py-1 text-sm font-bold ${meta.bg} ${meta.text}`}>
          {meta.label}
        </span>
      </div>
      <p className="mt-2 text-xs text-gray-400">
        예측 승객 {Math.round(congestion.pax_pred).toLocaleString()}명 · 기준 p80{" "}
        {congestion.p80?.toLocaleString()}
      </p>
      {congestion.better_hours.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {congestion.better_hours.map((b) => (
            <span
              key={b.hour}
              className="rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700"
            >
              {b.hour}시 출발 시 '{b.level}'
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
