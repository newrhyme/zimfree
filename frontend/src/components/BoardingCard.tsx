import { DoorOpen, MapPin } from "lucide-react";
import type { Boarding } from "../types";
import WarningBanner from "./WarningBanner";

export default function BoardingCard({ boarding }: { boarding: Boarding }) {
  if (!boarding.door_pos) {
    return (
      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <p className="text-gray-500">{boarding.message ?? "탑승칸 추천 정보 없음"}</p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl bg-navy-900 p-5 text-white shadow-md">
      <div className="flex items-center gap-2 text-sm text-blue-200">
        <DoorOpen size={16} /> 추천 탑승 위치
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-5xl font-black tracking-tight">{boarding.door_pos}</span>
        <span className="text-lg text-blue-100">위치에 타세요</span>
      </div>
      {boarding.elevator_note && (
        <div className="mt-3 flex items-start gap-2 rounded-xl bg-navy-800 p-3 text-sm text-blue-100">
          <MapPin size={16} className="mt-0.5 shrink-0" />
          <span>도착역 엘리베이터: {boarding.elevator_note}</span>
        </div>
      )}
      <WarningBanner warnings={boarding.warnings} />
    </div>
  );
}
