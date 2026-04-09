"use client";

export type BarDatum = { label: string; value: number };

export function BarChart({ data }: { data: BarDatum[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <div className="text-sm font-semibold">Calls by Day</div>
      <div className="mt-4 grid gap-2">
        {data.length === 0 ? (
          <div className="text-sm text-zinc-500">No data yet.</div>
        ) : (
          data.map((d) => (
            <div key={d.label} className="grid grid-cols-12 items-center gap-3">
              <div className="col-span-3 truncate text-xs text-zinc-600">{d.label}</div>
              <div className="col-span-8">
                <div className="h-2 w-full rounded-full bg-zinc-100">
                  <div
                    className="h-2 rounded-full bg-zinc-900"
                    style={{ width: `${Math.round((d.value / max) * 100)}%` }}
                  />
                </div>
              </div>
              <div className="col-span-1 text-right text-xs font-semibold text-zinc-700">
                {d.value}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
