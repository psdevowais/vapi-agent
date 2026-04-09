"use client";

export type ChatMessage = {
  id?: string;
  role: "user" | "agent";
  text: string;
  ts: number;
};

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ConversationBox({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white">
      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="text-sm font-semibold">Live Conversation</div>
        <div className="text-xs text-zinc-500">Messages appear in real time</div>
      </div>
      <div className="max-h-[420px] overflow-auto p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-zinc-500">No messages yet.</div>
        ) : (
          <div className="space-y-3">
            {messages.map((m, idx) => (
              <div key={idx} className="flex gap-3">
                <div
                  className={`mt-0.5 h-7 w-7 shrink-0 rounded-full ${
                    m.role === "agent" ? "bg-zinc-900" : "bg-zinc-200"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-4">
                    <div className="text-xs font-semibold text-zinc-700">
                      {m.role === "agent" ? "Aria" : "You"}
                    </div>
                    <div className="text-xs text-zinc-400">{formatTime(m.ts)}</div>
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-sm text-zinc-900">{m.text}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
