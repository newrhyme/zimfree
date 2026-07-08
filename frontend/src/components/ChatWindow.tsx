import { useRef, useState } from "react";
import { Send } from "lucide-react";
import { api } from "../api/client";

interface Msg {
  role: "user" | "assistant";
  text: string;
  tools?: string[];
}

const EXAMPLES = [
  "해운대 가는데 캐리어 두 개야, 짐 어떻게 할까?",
  "서면역 금요일 저녁 붐벼? 언제 가면 좋아?",
  "배터리 15%인데 부산역에서 충전할 데 있어?",
];

export default function ChatWindow({ disabled }: { disabled: boolean }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    if (!text.trim() || busy || disabled) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat(text);
      setMsgs((m) => [...m, { role: "assistant", text: res.reply, tools: res.tools_used }]);
    } catch (e) {
      setMsgs((m) => [
        ...m,
        { role: "assistant", text: `오류: ${(e as Error).message}` },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 50);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {msgs.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-gray-500">예시 질문을 눌러보세요</p>
            {EXAMPLES.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                disabled={disabled}
                className="block w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
                m.role === "user"
                  ? "bg-navy-900 text-white"
                  : "bg-white text-gray-800 shadow-sm"
              }`}
            >
              {m.text}
              {m.tools && m.tools.length > 0 && (
                <div className="mt-1.5 text-[10px] text-gray-400">
                  🔧 {m.tools.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-white px-4 py-3 shadow-sm">
              <span className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.2s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.1s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-gray-200 bg-white p-3">
        {disabled && (
          <p className="mb-2 text-center text-xs text-amber-600">
            API 키 미설정 — 데모에서는 플래너 기능을 이용하세요
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled || busy}
            placeholder={disabled ? "어시스턴트 비활성" : "무엇이든 물어보세요"}
            className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={disabled || busy}
            className="rounded-xl bg-navy-900 px-4 text-white disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
