import { AlertTriangle } from "lucide-react";

export default function WarningBanner({ warnings }: { warnings: string[] }) {
  if (!warnings || warnings.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl bg-amber-50 border border-amber-300 p-3">
      {warnings.map((w, i) => (
        <div key={i} className="flex items-start gap-2 text-amber-800 text-sm">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>{w}</span>
        </div>
      ))}
    </div>
  );
}
