"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import Vapi from "@vapi-ai/web";

import { VAPI_ASSISTANT_ID, VAPI_PUBLIC_KEY, getWsUrl } from "@/lib/config";

import { ChatMessage, ConversationBox } from "@/components/ConversationBox";

type ConnectionState = "disconnected" | "connecting" | "connected";

type WsEvent =
  | { type: "session"; call_id: string }
  | { type: "bound"; call_id: string }
  | {
      type: "transcript_event";
      id: string;
      call_id: string;
      role: string;
      text: string;
      occurred_at: string | null;
    }
  | { type: "agent_text"; text: string }
  | { type: "stt_partial"; text: string }
  | { type: "stt_final"; text: string }
  | { type: "tts_wav"; audio_base64: string }
  | { type: "audio_ready" }
  | { type: "error"; message: string }
  | { type: "pong" };

export function VoiceInterface() {
  const [conn, setConn] = useState<ConnectionState>("disconnected");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const localCallIdRef = useRef<string | null>(null);
  const vapiRef = useRef<Vapi | null>(null);
  const vapiBoundRef = useRef<boolean>(false);
  const vapiActiveRef = useRef<boolean>(false);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const ttsUrlRef = useRef<string | null>(null);
  const downsampleStateRef = useRef<{ prev: Float32Array | null }>({ prev: null });
  const lastBargeInAtRef = useRef<number>(0);
  const [sttPartial, setSttPartial] = useState<string>("");

  function tryPersistTranscript(ws: WebSocket, role: string, text: string) {
    if (ws.readyState !== WebSocket.OPEN) return;
    const trimmed = (text || "").trim();
    if (!trimmed) return;
    ws.send(
      JSON.stringify({
        type: "persist_transcript",
        role,
        text: trimmed,
        occurred_at: new Date().toISOString(),
      }),
    );
  }

  function tryPersistLead(ws: WebSocket, lead: unknown) {
    if (ws.readyState !== WebSocket.OPEN) return;
    if (!lead || typeof lead !== "object") return;
    ws.send(JSON.stringify({ type: "persist_lead", lead }));
  }

  const statusText = useMemo(() => {
    if (conn === "connected") return "Connected";
    if (conn === "connecting") return "Connecting…";
    return "Disconnected";
  }, [conn]);

  useEffect(() => {
    return () => {
      try {
        vapiRef.current?.stop();
      } catch {}
      vapiActiveRef.current = false;
      stopAudio();
      stopTts();
      wsRef.current?.close();
    };
  }, []);

  function appendOrMergeMessage(next: ChatMessage) {
    const text = (next.text || "").trim();
    if (!text) return;

    setMessages((prev) => {
      // If we have an id, check for existing message with same id
      if (next.id) {
        const existingIdx = prev.findIndex((m) => m.id === next.id);
        if (existingIdx !== -1) {
          // Update existing message
          const updated = [...prev];
          updated[existingIdx] = { ...updated[existingIdx], text, ts: next.ts };
          return updated;
        }
      }

      const last = prev[prev.length - 1];
      if (!last) return [{ ...next, id: next.id || `msg-${Date.now()}` }];

      const withinWindow = Math.abs(next.ts - last.ts) <= 3000;
      const sameRole = last.role === next.role;

      // If same role within 3 seconds, merge/update
      if (withinWindow && sameRole) {
        const lastText = (last.text || "").trim();
        // Check if texts overlap or one extends the other
        if (text.startsWith(lastText) || lastText.startsWith(text) || lastText.includes(text) || text.includes(lastText)) {
          const mergedText = text.length >= lastText.length ? text : lastText;
          // Keep the same id if merging with last message
          const mergedId = last.id || next.id || `msg-${last.ts}`;
          return [...prev.slice(0, -1), { ...last, id: mergedId, text: mergedText, ts: next.ts }];
        }
      }

      // Check for exact duplicate
      if (withinWindow && sameRole && last.text.trim() === text) {
        return prev;
      }

      return [...prev, { ...next, id: next.id || `msg-${Date.now()}` }];
    });
  }

  function stopTts() {
    try {
      if (ttsAudioRef.current) {
        ttsAudioRef.current.pause();
        ttsAudioRef.current.currentTime = 0;
      }
    } catch {}

    if (ttsUrlRef.current) {
      try {
        URL.revokeObjectURL(ttsUrlRef.current);
      } catch {}
      ttsUrlRef.current = null;
    }
  }

  function floatTo16BitPCM(input: Float32Array): Int16Array {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      let s = Math.max(-1, Math.min(1, input[i] ?? 0));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  function downsampleTo16kHz(input: Float32Array, inSampleRate: number): Float32Array {
    if (inSampleRate === 16000) return input;

    const ratio = inSampleRate / 16000;
    const newLen = Math.floor(input.length / ratio);
    const out = new Float32Array(newLen);
    let offset = 0;
    for (let i = 0; i < newLen; i++) {
      const nextOffset = Math.floor((i + 1) * ratio);
      let sum = 0;
      let count = 0;
      for (let j = offset; j < nextOffset && j < input.length; j++) {
        sum += input[j] ?? 0;
        count++;
      }
      out[i] = count > 0 ? sum / count : 0;
      offset = nextOffset;
    }
    return out;
  }

  async function startAudio(ws: WebSocket) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;

    const source = audioCtx.createMediaStreamSource(stream);
    sourceRef.current = source;

    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    const inRate = audioCtx.sampleRate;
    downsampleStateRef.current.prev = null;

    processor.onaudioprocess = (e) => {
      if (ws.readyState !== WebSocket.OPEN) return;

      const input = e.inputBuffer.getChannelData(0);
      const ds = downsampleTo16kHz(input, inRate);
      const pcm16 = floatTo16BitPCM(ds);
      ws.send(pcm16.buffer);
    };

    source.connect(processor);
    const zeroGain = audioCtx.createGain();
    zeroGain.gain.value = 0;
    processor.connect(zeroGain);
    zeroGain.connect(audioCtx.destination);

    ws.send(JSON.stringify({ type: "start_audio" }));
  }

  function stopAudio() {
    try {
      processorRef.current?.disconnect();
    } catch {}
    try {
      sourceRef.current?.disconnect();
    } catch {}
    try {
      audioCtxRef.current?.close();
    } catch {}
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    } catch {}

    processorRef.current = null;
    sourceRef.current = null;
    audioCtxRef.current = null;
    streamRef.current = null;
  }

  function playWavBase64(b64: string) {
    try {
      console.debug("TTS: received base64 length", b64?.length ?? 0);
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/wav" });
      const url = URL.createObjectURL(blob);

      if (!ttsAudioRef.current) {
        const audio = new Audio();
        audio.preload = "auto";
        audio.onerror = () => {
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: "Error: audio decode/playback failed", ts: Date.now() },
          ]);
        };
        ttsAudioRef.current = audio;
      }

      try {
        ttsAudioRef.current.pause();
        ttsAudioRef.current.currentTime = 0;
      } catch {}

      if (ttsUrlRef.current) {
        try {
          URL.revokeObjectURL(ttsUrlRef.current);
        } catch {}
      }

      ttsUrlRef.current = url;
      ttsAudioRef.current.src = url;
      ttsAudioRef.current.onended = () => {
        if (ttsUrlRef.current) {
          try {
            URL.revokeObjectURL(ttsUrlRef.current);
          } catch {}
          ttsUrlRef.current = null;
        }
      };
      void ttsAudioRef.current.play().catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        console.error("TTS: play() rejected", e);
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: `Error: audio play blocked (${msg})`, ts: Date.now() },
        ]);
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Error: failed to play audio", ts: Date.now() },
      ]);
    }
  }

  function connect() {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConn("connecting");
    const ws = new WebSocket(getWsUrl());
    wsRef.current = ws;
    localCallIdRef.current = null;
    vapiBoundRef.current = false;

    ws.onopen = () => {
      console.log("[WS] WebSocket opened successfully");
      setConn("connected");
      setMessages([]);
      setSttPartial("");
      stopTts();

      const canUseVapi = Boolean(VAPI_PUBLIC_KEY && VAPI_ASSISTANT_ID);
      console.log("[Vapi] canUseVapi:", canUseVapi, "Key exists:", Boolean(VAPI_PUBLIC_KEY), "Assistant exists:", Boolean(VAPI_ASSISTANT_ID));
      
      if (canUseVapi) {
        try {
          console.log("[Vapi] Initializing Vapi SDK...");
          const vapi = new Vapi(VAPI_PUBLIC_KEY);
          vapiRef.current = vapi;
          vapiActiveRef.current = true;

          vapi.on("message", (message: any) => {
            console.log("[Vapi] message event:", message?.type, message);
            if (!vapiBoundRef.current && message?.call?.id && ws.readyState === WebSocket.OPEN) {
              vapiBoundRef.current = true;
              ws.send(JSON.stringify({ type: "bind", vapi_call_id: String(message.call.id) }));
            }

            if (
              message?.type === "transport" &&
              (message?.state === "disconnected" || message?.status === "disconnected")
            ) {
              appendOrMergeMessage({
                role: "agent",
                text: "Call ended (connection lost).",
                ts: Date.now(),
              });
              disconnect();
              return;
            }

            if (
              message?.type === "status" &&
              typeof message?.status === "string" &&
              message.status.toLowerCase().includes("disconnected")
            ) {
              appendOrMergeMessage({
                role: "agent",
                text: "Call ended (connection lost).",
                ts: Date.now(),
              });
              disconnect();
              return;
            }

            if (
              message?.type === "call-end" ||
              message?.type === "hangup" ||
              message?.type === "end" ||
              message?.event === "call.end"
            ) {
              setMessages((prev) => [
                ...prev,
                { role: "agent", text: "Call ended.", ts: Date.now() },
              ]);
              disconnect();
              return;
            }

            if (message?.type === "transcript") {
              const role: ChatMessage["role"] =
                message.role === "assistant" || message.role === "agent" ? "agent" : "user";
              const text =
                typeof message.transcript === "string"
                  ? message.transcript
                  : message.transcript?.text ?? "";
              if (text) {
                appendOrMergeMessage({ role, text, ts: Date.now() });
                tryPersistTranscript(
                  ws,
                  message.role === "assistant" || message.role === "agent" ? "agent" : "user",
                  text,
                );
              }
            }

            const toolName =
              message?.tool?.name ||
              message?.function?.name ||
              (typeof message?.name === "string" ? message.name : null);
            const toolArgs =
              message?.tool?.arguments ||
              message?.tool?.args ||
              message?.function?.arguments ||
              message?.args ||
              null;

            if (typeof toolName === "string" && toolName.toLowerCase() === "save_lead") {
              if (toolArgs && typeof toolArgs === "object") {
                tryPersistLead(ws, toolArgs);
              }
            }

            const toolCalls = message?.toolCalls || message?.tool_calls;
            if (Array.isArray(toolCalls)) {
              for (const item of toolCalls) {
                const fn = item?.function;
                const name = fn?.name;
                let args: any = fn?.arguments;
                if (typeof name === "string" && name.toLowerCase() === "save_lead") {
                  if (typeof args === "string") {
                    try {
                      args = JSON.parse(args);
                    } catch {
                      args = null;
                    }
                  }
                  if (args && typeof args === "object") {
                    tryPersistLead(ws, args);
                  }
                }
              }
            }
          });

          vapi.on("error", (e: any) => {
            console.error("[Vapi] Error event:", e);
            const msg =
              e instanceof Error
                ? e.message
                : typeof e === "string"
                  ? e
                  : typeof e?.message === "string"
                    ? e.message
                    : (() => {
                        try {
                          return JSON.stringify(e);
                        } catch {
                          return String(e);
                        }
                      })();
            console.error("[Vapi] Error message:", msg);
            setMessages((prev) => [
              ...prev,
              { role: "agent", text: `Vapi Error: ${msg}`, ts: Date.now() },
            ]);

            if (msg.toLowerCase().includes("meeting ended") || msg.toLowerCase().includes("ejection")) {
              disconnect();
            }
          });

          console.log("[Vapi] Starting assistant:", VAPI_ASSISTANT_ID);
          vapi.start(VAPI_ASSISTANT_ID);
        } catch (err) {
          console.error("[Vapi] Synchronous error during init:", err);
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: "Error: failed to start Vapi session", ts: Date.now() },
          ]);
        }
        return;
      }

      void startAudio(ws).catch(() => {
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: "Error: microphone access failed", ts: Date.now() },
        ]);
      });
    };

    ws.onclose = (event) => {
      console.log("[WS] WebSocket closed:", event.code, event.reason);
      try {
        vapiRef.current?.stop();
      } catch {}
      vapiRef.current = null;
      vapiActiveRef.current = false;
      stopAudio();
      stopTts();
      setConn("disconnected");
    };

    ws.onerror = (error) => {
      console.error("[WS] WebSocket error:", error);
      try {
        vapiRef.current?.stop();
      } catch {}
      vapiRef.current = null;
      vapiActiveRef.current = false;
      stopAudio();
      stopTts();
      setConn("disconnected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsEvent;
        console.log("[WS] Message received:", data.type, data);
        if (data.type === "session") {
          localCallIdRef.current = data.call_id;
          return;
        }
        if (data.type === "bound") {
          return;
        }
        if (data.type === "transcript_event") {
          if (vapiActiveRef.current) {
            return;
          }
          const role: ChatMessage["role"] =
            data.role === "assistant" || data.role === "agent" ? "agent" : "user";
          appendOrMergeMessage({ id: data.id, role, text: data.text, ts: Date.now() });
          return;
        }
        if (data.type === "stt_partial") {
          setSttPartial(data.text);
          const now = Date.now();
          const shouldBargeIn = (data.text || "").trim().length >= 3 && now - lastBargeInAtRef.current > 650;
          if (shouldBargeIn) {
            lastBargeInAtRef.current = now;
            stopTts();
          }
        }
        if (data.type === "stt_final") {
          setSttPartial("");
          setMessages((prev) => [...prev, { role: "user", text: data.text, ts: Date.now() }]);
        }
        if (data.type === "agent_text") {
          setMessages((prev) => [...prev, { role: "agent", text: data.text, ts: Date.now() }]);
        }
        if (data.type === "tts_wav") {
          console.debug("WS: tts_wav event");
          playWavBase64(data.audio_base64);
        }
        if (data.type === "error") {
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: `Error: ${data.message}`, ts: Date.now() },
          ]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: "Error: invalid message from server", ts: Date.now() },
        ]);
      }
    };
  }

  function disconnect() {
    try {
      vapiRef.current?.stop();
    } catch {}
    vapiRef.current = null;
    vapiActiveRef.current = false;
    stopAudio();
    stopTts();
    wsRef.current?.close();
    wsRef.current = null;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-2">
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold">Session</div>
              <div className="text-xs text-zinc-500">Continuous mic streaming (Option B)</div>
            </div>
            <div className="text-xs font-semibold text-zinc-700">{statusText}</div>
          </div>

          <div className="mt-4 flex flex-col gap-2">
            {conn !== "connected" ? (
              <button
                onClick={connect}
                className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-semibold text-white hover:bg-zinc-800"
              >
                Start Call
              </button>
            ) : (
              <button
                onClick={disconnect}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-900 hover:bg-zinc-50"
              >
                End Call
              </button>
            )}

            <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3">
              <div className="text-xs font-semibold text-zinc-700">Live STT</div>
              <div className="mt-1 text-sm text-zinc-800">
                {conn === "connected" ? (sttPartial || "Listening…") : "—"}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-sm font-semibold">Notes</div>
          <div className="mt-1 text-xs text-zinc-500">
            STT/TTS streaming is active. Start a call and speak normally.
          </div>
        </div>
      </div>

      <div className="lg:col-span-3">
        <ConversationBox messages={messages} />
      </div>
    </div>
  );
}
