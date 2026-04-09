'use client';

import { useEffect, useState } from "react";

import { BarChart } from "@/components/BarChart";
import { Shell } from "@/components/Shell";
import { getAnalytics, AnalyticsSummary } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";

function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics()
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !summary) {
    return (
      <Shell>
        <div className="text-center py-12 text-zinc-600">Loading...</div>
      </Shell>
    );
  }

  const callsByDay = summary.calls_by_day ?? [];
  const data = callsByDay.map((d) => ({
    label: d.day,
    value: d.count,
  }));

  const callsToday = summary.calls_today ?? 0;
  const vapi = summary.vapi;

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  }

  function formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }

  return (
    <Shell>
      <div className="mb-6">
        <div className="text-2xl font-semibold">Analytics</div>
        <div className="mt-1 text-sm text-zinc-600">Call metrics and usage statistics.</div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4 mb-6">
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500">Total Calls</div>
          <div className="mt-1 text-2xl font-semibold text-zinc-900">{summary.total_calls}</div>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500">Calls Today</div>
          <div className="mt-1 text-2xl font-semibold text-zinc-900">{callsToday}</div>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500">This Week</div>
          <div className="mt-1 text-2xl font-semibold text-zinc-900">{summary.calls_this_week ?? 0}</div>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500">This Month</div>
          <div className="mt-1 text-2xl font-semibold text-zinc-900">{summary.calls_this_month ?? 0}</div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mb-6">
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500 mb-3">Lead Priority</div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-zinc-500">Urgent Leads</div>
              <div className="text-xl font-semibold text-red-600">{summary.urgent_leads ?? 0}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-500">Normal Leads</div>
              <div className="text-xl font-semibold text-zinc-700">{summary.normal_leads ?? 0}</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500 mb-3">Call Status</div>
          <div className="space-y-2">
            {summary.calls_by_status.map((s) => (
              <div key={s.status} className="flex justify-between items-center">
                <span className="text-sm text-zinc-600">{s.status || 'Unknown'}</span>
                <span className="text-sm font-medium">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {vapi && (
        <div className="rounded-xl border border-zinc-200 bg-white mb-6">
          <div className="border-b border-zinc-200 px-4 py-3">
            <div className="text-sm font-semibold">Vapi Analytics</div>
            <div className="text-xs text-zinc-500">Real-time stats from Vapi API</div>
          </div>

          <div className="p-4">
            <div className="grid gap-6 lg:grid-cols-4 mb-6">
              <div>
                <div className="text-xs text-zinc-500">Vapi Calls</div>
                <div className="text-xl font-semibold text-zinc-900">{vapi.total_calls}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Failed</div>
                <div className="text-xl font-semibold text-red-600">{vapi.failed_calls}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">In Progress</div>
                <div className="text-xl font-semibold text-blue-600">{vapi.in_progress_calls}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Ended</div>
                <div className="text-xl font-semibold text-green-600">{vapi.ended_calls}</div>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-3 mb-6">
              <div>
                <div className="text-xs text-zinc-500">Total Cost</div>
                <div className="text-xl font-semibold text-zinc-900">{formatCost(vapi.total_cost)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Total Duration</div>
                <div className="text-xl font-semibold text-zinc-900">{formatDuration(vapi.total_duration_seconds)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Avg Duration</div>
                <div className="text-xl font-semibold text-zinc-900">{formatDuration(vapi.avg_duration_seconds)}</div>
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold text-zinc-500 mb-3">Status Breakdown</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {Object.entries(vapi.status_breakdown).map(([status, count]) => (
                  <div key={status} className="bg-zinc-50 rounded-lg p-3">
                    <div className="text-xs text-zinc-500 capitalize">{status.replace('-', ' ')}</div>
                    <div className="text-lg font-semibold text-zinc-900">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {data.length > 0 && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold text-zinc-500 mb-3">Calls by Day</div>
          <BarChart data={data} />
        </div>
      )}
    </Shell>
  );
}

export default withAuth(AnalyticsPage);
