'use client';

import Link from "next/link";
import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { getCalls, CallSummary } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";

function CallsPage() {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCalls()
      .then(setCalls)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <Shell>
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold">Calls</div>
          <div className="mt-1 text-sm text-zinc-600">All call sessions stored locally.</div>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-4 py-3">
          <div className="text-sm font-semibold">Call List</div>
          <div className="text-xs text-zinc-500">Click a call to view details.</div>
        </div>
        <div className="overflow-auto">
          {loading ? (
            <div className="px-4 py-6 text-zinc-500 text-center">Loading...</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-200 text-xs uppercase text-zinc-500">
                <tr>
                  <th className="px-4 py-3">Call ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Started</th>
                  <th className="px-4 py-3">Ended</th>
                  <th className="px-4 py-3">Transcript</th>
                  <th className="px-4 py-3">Leads</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-zinc-500" colSpan={6}>
                      No calls yet.
                    </td>
                  </tr>
                ) : (
                  calls.map((c) => (
                    <tr key={c.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                      <td className="px-4 py-3 font-medium text-zinc-900">
                        <Link className="hover:underline" href={`/calls/${c.id}`}>
                          {c.id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-zinc-700">{c.status || "—"}</td>
                      <td className="px-4 py-3 text-zinc-700">
                        {c.started_at ? new Date(c.started_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3 text-zinc-700">
                        {c.ended_at ? new Date(c.ended_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3 text-zinc-700">
                        {typeof c.transcript_event_count === "number" ? c.transcript_event_count : "—"}
                      </td>
                      <td className="px-4 py-3 text-zinc-700">
                        {typeof c.lead_count === "number" ? c.lead_count : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Shell>
  );
}

export default withAuth(CallsPage);
