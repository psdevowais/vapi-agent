'use client';

import { Shell } from "@/components/Shell";
import { SettingsClient } from "@/app/settings/SettingsClient";
import { withAuth } from "@/lib/withAuth";

function SettingsPage() {
  return (
    <Shell>
      <div className="mb-6">
        <div className="text-2xl font-semibold">Settings</div>
        <div className="mt-1 text-sm text-zinc-600">Manage Google Sheets integration.</div>
      </div>

      <SettingsClient />
    </Shell>
  );
}

export default withAuth(SettingsPage);
