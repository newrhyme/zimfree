import { useEffect, useState } from "react";
import ChatWindow from "../components/ChatWindow";
import { api } from "../api/client";

export default function Assistant() {
  const [enabled, setEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .assistantStatus()
      .then((s) => setEnabled(s.enabled))
      .catch(() => setEnabled(false));
  }, []);

  if (enabled === null) {
    return <div className="p-4 text-sm text-gray-400">어시스턴트 상태 확인 중…</div>;
  }
  return <ChatWindow disabled={!enabled} />;
}
