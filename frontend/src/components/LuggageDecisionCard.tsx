import { Briefcase, Lock, Truck } from "lucide-react";
import type { LuggageDecision, LuggageOption } from "../types";

const LABEL: Record<string, { icon: JSX.Element; title: string }> = {
  carry: { icon: <Briefcase size={18} />, title: "휴대" },
  locker: { icon: <Lock size={18} />, title: "보관함" },
  delivery: { icon: <Truck size={18} />, title: "짐배송" },
};

function optionBody(o: LuggageOption) {
  if (o.type === "carry") return <p className="text-sm text-gray-600">난이도 <b>{o.difficulty}</b> · {o.reason}</p>;
  if (o.type === "locker")
    return (
      <p className="text-sm text-gray-600">
        {o.available ? (
          <>
            <b>{o.station}</b> · {o.reason}
            {o.fee && <span className="block text-xs text-gray-400">{o.fee}</span>}
          </>
        ) : (
          <span className="text-gray-400">{o.reason}</span>
        )}
      </p>
    );
  return (
    <p className="text-sm text-gray-600">
      {o.prior != null && <b>{Math.round(o.prior * 100)}% </b>}
      {o.reason}
    </p>
  );
}

export default function LuggageDecisionCard({ decision }: { decision: LuggageDecision }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700">짐 처리 추천</h3>
      <div className="mt-3 space-y-2">
        {decision.options.map((o) => {
          const meta = LABEL[o.type];
          const recommended = decision.recommendation === o.type;
          return (
            <div
              key={o.type}
              className={`rounded-xl border p-3 ${
                recommended ? "border-navy-700 bg-navy-900/5 ring-1 ring-navy-700" : "border-gray-200"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-navy-800">{meta.icon}</span>
                <span className="font-semibold text-gray-800">{meta.title}</span>
                {recommended && (
                  <span className="ml-auto rounded-full bg-navy-900 px-2 py-0.5 text-xs font-bold text-white">
                    추천
                  </span>
                )}
              </div>
              <div className="mt-1">{optionBody(o)}</div>
            </div>
          );
        })}
      </div>
      {decision.source_notes.length > 0 && (
        <ul className="mt-3 space-y-1">
          {decision.source_notes.map((s, i) => (
            <li key={i} className="text-xs text-gray-400">
              📊 {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
