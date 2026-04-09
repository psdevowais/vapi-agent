import { API_BASE_URL } from "@/lib/config";

export type CallSummary = {
  id: string;
  created_at: string;
  ended_at: string | null;
  status?: string;
  started_at?: string | null;
  transcript_event_count?: number;
  lead_count?: number;
};

export type CallMessage = {
  id: string;
  role: "user" | "agent";
  content: string;
  created_at: string;
};

export type CallDetail = CallSummary & {
  transcript_events: {
    id: string;
    role: string;
    text: string;
    occurred_at: string | null;
    created_at: string;
  }[];
  leads: {
    id: number;
    call: string | null;
    caller_name: string;
    caller_phone: string;
    caller_email: string;
    call_reason: string;
    call_priority: string;
    property_address: string;
    occupancy_status: string;
    sell_timeframe: string;
    additional_notes: string;
    intent: string;
    query_description: string;
    update_topic: string;
    created_at: string;
  }[];
};

export type AnalyticsSummary = {
  total_calls: number;
  calls_by_status: { status: string; count: number }[];
  calls_by_day?: { day: string; count: number }[];
  calls_today?: number;
  calls_this_week?: number;
  calls_this_month?: number;
  urgent_leads?: number;
  normal_leads?: number;
  vapi?: {
    total_calls: number;
    failed_calls: number;
    in_progress_calls: number;
    ended_calls: number;
    total_cost: number;
    total_duration_seconds: number;
    avg_duration_seconds: number;
    status_breakdown: Record<string, number>;
  };
};

function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();

  if (!token) {
    throw new Error('No authentication token found');
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Token ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return (await res.json()) as T;
}

export function getCalls(): Promise<CallSummary[]> {
  return apiFetch<CallSummary[]>("/calls");
}

export function getCall(callId: string): Promise<CallDetail> {
  return apiFetch<CallDetail>(`/calls/${callId}`);
}

export function getAnalytics(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>("/analytics");
}

export type GoogleAuthStatus = {
  is_authorized: boolean;
};

export type GoogleAuthUrl = {
  authorization_url: string;
};

export function getGoogleAuthStatus(): Promise<GoogleAuthStatus> {
  return apiFetch<GoogleAuthStatus>("/auth/google/status");
}

export function getGoogleAuthUrl(): Promise<GoogleAuthUrl> {
  return apiFetch<GoogleAuthUrl>("/auth/google");
}

export function disconnectGoogle(): Promise<{ disconnected: boolean }> {
  return apiFetch<{ disconnected: boolean }>("/auth/google/disconnect", {
    method: "DELETE",
  });
}

export type SyncResult = {
  status: string;
  message: string;
};

export function syncSheetsToDB(): Promise<SyncResult> {
  return apiFetch<SyncResult>("/sheets/sync", {
    method: "POST",
  });
}

// Twilio Outbound Calling
export type OutboundCallRequest = {
  phone_number: string;
};

export type OutboundCallResponse = {
  call_id: string;
  twilio_call_sid: string;
  status: string;
  phone_number: string;
};

export function initiateOutboundCall(phoneNumber: string): Promise<OutboundCallResponse> {
  return apiFetch<OutboundCallResponse>("/twilio/outbound", {
    method: "POST",
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
}

export function getCallStatus(callId: string): Promise<CallDetail> {
  return apiFetch<CallDetail>(`/twilio/calls/${callId}/status`);
}

export function endCall(callId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/twilio/calls/${callId}/end`, {
    method: "POST",
  });
}
