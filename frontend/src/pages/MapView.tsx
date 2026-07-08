import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { api, LINE_COLOR } from "../api/client";
import type { Facilities, Station } from "../types";

function FacilityPopup({ code }: { code: number }) {
  const [fac, setFac] = useState<Facilities | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api
      .facilities(code)
      .then((f) => alive && setFac(f))
      .catch(() => alive && setFac(null))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [code]);

  if (loading) return <span className="text-xs text-gray-400">불러오는 중…</span>;
  if (!fac) return <span className="text-xs text-gray-400">정보 없음</span>;

  const row = (icon: string, label: string, n: number) => (
    <div className="flex items-center justify-between gap-4 text-xs">
      <span>
        {icon} {label}
      </span>
      <span className={n > 0 ? "font-semibold text-gray-800" : "text-gray-400"}>
        {n > 0 ? `${n}` : "정보 없음"}
      </span>
    </div>
  );

  return (
    <div className="space-y-1">
      {row("🛅", "보관함", fac.lockers.length)}
      {row("🔌", "충전기", fac.chargers.length)}
      {row("🏧", "ATM", fac.atms.length)}
      {row("♿", "키오스크", fac.kiosks.length)}
      {row("🛗", "엘리베이터", fac.elevators_count)}
      {row("↗️", "에스컬레이터", fac.escalators_count)}
    </div>
  );
}

export default function MapView({ stations }: { stations: Station[] }) {
  return (
    <div className="h-[calc(100vh-8.5rem)]">
      <MapContainer
        center={[35.16, 129.06]}
        zoom={12}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {stations.map((s) => (
          <CircleMarker
            key={s.station_code}
            center={[s.lat, s.lng]}
            radius={5}
            pathOptions={{
              color: LINE_COLOR[s.line] ?? "#555",
              fillColor: LINE_COLOR[s.line] ?? "#555",
              fillOpacity: 0.85,
              weight: 1,
            }}
          >
            <Popup>
              <div className="min-w-[160px]">
                <div className="mb-1 font-bold text-gray-800">
                  {s.std_name}{" "}
                  <span className="text-xs font-normal text-gray-400">{s.line}</span>
                </div>
                <FacilityPopup code={s.station_code} />
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
