'use client';

import Link from "next/link";
import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { getCall, CallDetail } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";

function CallDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [call, setCall] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [callId, setCallId] = useState<string>("");

  useEffect(() => {
    params.then((p) => {
      setCallId(p.id);
      getCall(p.id)
        .then(setCall)
        .catch(console.error)
        .finally(() => setLoading(false));
    });
  }, [params]);

  if (loading || !call) {
    return (
      <Shell>
        <div className="text-center py-12 text-zinc-600">Loading...</div>
      </Shell>
    );
  }

  const transcript = call.transcript_events ?? [];
  const leads = call.leads ?? [];
  const lead = leads[0] ?? null;

  return (
    <Shell>
      <div className="mb-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-2xl font-semibold">Call Detail</div>
            <div className="mt-1 text-sm text-zinc-600 break-all">{call.id}</div>
          </div>
          <Link
            href="/calls"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-900 hover:bg-zinc-50"
          >
            Back
          </Link>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-zinc-200 bg-white p-4">
            <div className="text-sm font-semibold">Metadata</div>
            <div className="mt-3 grid gap-2 text-sm">
              <div className="flex items-center justify-between gap-4">
                <div className="text-zinc-500">Created</div>
                <div className="font-medium text-zinc-900">
                  {new Date(call.created_at).toLocaleString()}
                </div>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div className="text-zinc-500">Ended</div>
                <div className="font-medium text-zinc-900">
                  {call.ended_at ? new Date(call.ended_at).toLocaleString() : "—"}
                </div>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div className="text-zinc-500">Messages</div>
                <div className="font-medium text-zinc-900">{transcript.length}</div>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-4">
            <div className="text-sm font-semibold">Lead</div>
            <div className="mt-1 text-xs text-zinc-500">
              Saved details captured during the call.
            </div>

            {!lead ? (
              <div className="mt-3 text-sm text-zinc-500">No lead captured.</div>
            ) : (
              <div className="mt-3 grid gap-2 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Reason</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.call_reason || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Priority</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.call_priority || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Name</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.caller_name}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Phone</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.caller_phone}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Email</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.caller_email}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Occupancy</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.occupancy_status || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Timeline</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.sell_timeframe || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Intent</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.intent || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Query Description</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.query_description || "—"}</div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div className="text-zinc-500">Update Topic</div>
                  <div className="font-medium text-zinc-900 break-all">{lead.update_topic || "—"}</div>
                </div>
                <div className="mt-2">
                  <div className="text-zinc-500">Property Address</div>
                  <div className="mt-1 font-medium text-zinc-900 whitespace-pre-wrap">
                    {lead.property_address || "—"}
                  </div>
                </div>
                <div className="mt-2">
                  <div className="text-zinc-500">Notes</div>
                  <div className="mt-1 font-medium text-zinc-900 whitespace-pre-wrap">
                    {lead.additional_notes || "—"}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="rounded-xl border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3">
              <div className="text-sm font-semibold">Transcript</div>
              <div className="text-xs text-zinc-500">User and agent messages</div>
            </div>
            <div className="p-4">
              {transcript.length === 0 ? (
                <div className="text-sm text-zinc-500">No messages.</div>
              ) : (
                <div className="space-y-3">
                  {transcript.map((m) => (
                    <div key={m.id} className="rounded-lg border border-zinc-200 p-3">
                      <div className="flex items-center justify-between gap-4">
                        <div className="text-xs font-semibold text-zinc-700">
                          {m.role === "assistant" || m.role === "agent" ? "Aria" : "You"}
                        </div>
                        <div className="text-xs text-zinc-400">
                          {new Date(m.occurred_at ?? m.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                      <div className="mt-1 whitespace-pre-wrap text-sm text-zinc-900">
                        {m.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}

export default withAuth(CallDetailPage);
