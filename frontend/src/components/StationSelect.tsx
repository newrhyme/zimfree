import { useMemo, useState } from "react";
import type { Station } from "../types";

export default function StationSelect({
  stations,
  value,
  onChange,
  label,
}: {
  stations: Station[];
  value: number | null;
  onChange: (code: number) => void;
  label: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  const selected = stations.find((s) => s.station_code === value);
  const results = useMemo(() => {
    const term = q.trim();
    const list = term
      ? stations.filter(
          (s) => s.std_name.includes(term) || String(s.station_code) === term
        )
      : stations;
    // unique by std_name for the picker
    const seen = new Set<string>();
    return list.filter((s) => {
      if (seen.has(s.std_name)) return false;
      seen.add(s.std_name);
      return true;
    });
  }, [q, stations]);

  return (
    <div className="relative">
      <label className="mb-1 block text-xs font-medium text-gray-500">{label}</label>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-left text-sm"
      >
        {selected ? (
          <span className="font-medium text-gray-800">
            {selected.std_name}{" "}
            <span className="text-xs text-gray-400">({selected.line})</span>
          </span>
        ) : (
          <span className="text-gray-400">역 선택</span>
        )}
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-xl border border-gray-200 bg-white shadow-lg">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="역명 검색"
            className="w-full rounded-t-xl border-b border-gray-100 px-3 py-2 text-sm outline-none"
          />
          <ul className="max-h-56 overflow-y-auto">
            {results.slice(0, 40).map((s) => (
              <li key={s.station_code}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(s.station_code);
                    setOpen(false);
                    setQ("");
                  }}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50"
                >
                  <span className="text-gray-800">{s.std_name}</span>
                  <span className="text-xs text-gray-400">{s.line}</span>
                </button>
              </li>
            ))}
            {results.length === 0 && (
              <li className="px-3 py-3 text-sm text-gray-400">검색 결과 없음</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
