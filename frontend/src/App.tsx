import { useEffect, useState } from "react";
import { Bot, Map, Route } from "lucide-react";
import { api } from "./api/client";
import Planner from "./pages/Planner";
import Result from "./pages/Result";
import Assistant from "./pages/Assistant";
import MapView from "./pages/MapView";
import type { PlanRequest, RoutePlan, Station } from "./types";

type Tab = "planner" | "map" | "assistant";

const TABS: { id: Tab; label: string; icon: JSX.Element }[] = [
  { id: "planner", label: "플래너", icon: <Route size={20} /> },
  { id: "map", label: "지도", icon: <Map size={20} /> },
  { id: "assistant", label: "어시스턴트", icon: <Bot size={20} /> },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("planner");
  const [stations, setStations] = useState<Station[]>([]);
  const [plan, setPlan] = useState<RoutePlan | null>(null);
  const [req, setReq] = useState<PlanRequest | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .stations()
      .then(setStations)
      .catch((e) => setErr((e as Error).message));
  }, []);

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col bg-[#eef1f8]">
      <header className="bg-navy-900 px-4 py-3 text-white">
        <div className="flex items-center gap-2">
          <span className="text-xl">🧳</span>
          <div>
            <h1 className="text-lg font-black leading-none">짐프리</h1>
            <p className="text-[11px] text-blue-200">부산 지하철 여행 코파일럿</p>
          </div>
        </div>
      </header>

      {err && (
        <div className="bg-red-50 px-4 py-2 text-sm text-red-600">
          백엔드 연결 오류: {err}
        </div>
      )}

      <main className="flex-1 overflow-y-auto pb-20">
        {tab === "planner" &&
          (plan && req ? (
            <Result
              plan={plan}
              req={req}
              stations={stations}
              onBack={() => setPlan(null)}
            />
          ) : (
            <Planner
              stations={stations}
              onResult={(p, r) => {
                setPlan(p);
                setReq(r);
              }}
            />
          ))}
        {tab === "map" && <MapView stations={stations} />}
        {tab === "assistant" && <Assistant />}
      </main>

      <nav className="fixed bottom-0 left-1/2 w-full max-w-md -translate-x-1/2 border-t border-gray-200 bg-white">
        <div className="flex">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs ${
                tab === t.id ? "text-navy-900" : "text-gray-400"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
