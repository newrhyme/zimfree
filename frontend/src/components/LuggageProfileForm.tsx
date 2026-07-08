import { Baby, Minus, Plus } from "lucide-react";
import type { Luggage, Size } from "../types";

const SIZES: Size[] = ["S", "M", "L", "XL"];

export default function LuggageProfileForm({
  luggage,
  onChange,
}: {
  luggage: Luggage;
  onChange: (l: Luggage) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">캐리어 크기</label>
        <div className="flex gap-2">
          {SIZES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange({ ...luggage, size: s })}
              className={`flex-1 rounded-xl border py-2 text-sm font-semibold ${
                luggage.size === s
                  ? "border-navy-900 bg-navy-900 text-white"
                  : "border-gray-300 bg-white text-gray-600"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-gray-500">개수</label>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onChange({ ...luggage, count: Math.max(1, luggage.count - 1) })}
            className="rounded-lg border border-gray-300 p-1.5"
          >
            <Minus size={16} />
          </button>
          <span className="w-6 text-center font-bold">{luggage.count}</span>
          <button
            type="button"
            onClick={() => onChange({ ...luggage, count: luggage.count + 1 })}
            className="rounded-lg border border-gray-300 p-1.5"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={() => onChange({ ...luggage, stroller: !luggage.stroller })}
        className={`flex w-full items-center justify-between rounded-xl border px-3 py-2.5 ${
          luggage.stroller ? "border-navy-900 bg-navy-900/5" : "border-gray-300"
        }`}
      >
        <span className="flex items-center gap-2 text-sm text-gray-700">
          <Baby size={18} /> 유모차 동반
        </span>
        <span
          className={`relative h-6 w-11 rounded-full transition-colors ${
            luggage.stroller ? "bg-navy-900" : "bg-gray-300"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
              luggage.stroller ? "left-[22px]" : "left-0.5"
            }`}
          />
        </span>
      </button>
    </div>
  );
}
