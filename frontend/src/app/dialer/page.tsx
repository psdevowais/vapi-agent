'use client';

import { useEffect, useState, useCallback } from "react";

import { Shell } from "@/components/Shell";
import { initiateOutboundCall, endCall, getCallStatus, OutboundCallResponse } from "@/lib/api";
import { withAuth } from "@/lib/withAuth";

function PhoneIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  );
}

function CallEndIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
    </svg>
  );
}

type CallState = 'idle' | 'calling' | 'in-progress' | 'ended' | 'error';

function DialerPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [callState, setCallState] = useState<CallState>('idle');
  const [activeCall, setActiveCall] = useState<OutboundCallResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [duration, setDuration] = useState(0);
  const [isPolling, setIsPolling] = useState(false);

  // Poll for call status updates
  const pollCallStatus = useCallback(async (callId: string) => {
    try {
      const status = await getCallStatus(callId);
      
      // Map backend status to UI state
      if (status.status === 'completed' || status.status === 'ended') {
        setCallState('ended');
        setIsPolling(false);
      } else if (status.status === 'in_progress') {
        setCallState('in-progress');
      } else if (status.status && ['failed', 'busy', 'no_answer', 'canceled'].includes(status.status)) {
        setCallState('error');
        setError(`Call ${status.status.replace('_', ' ')}`);
        setIsPolling(false);
      }
    } catch (err) {
      console.error('Failed to get call status:', err);
    }
  }, []);

  // Start polling when call is active
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isPolling && activeCall?.call_id) {
      interval = setInterval(() => {
        pollCallStatus(activeCall.call_id);
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPolling, activeCall, pollCallStatus]);

  // Track call duration
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (callState === 'in-progress') {
      interval = setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [callState]);

  const handleCall = async () => {
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number');
      return;
    }

    // Validate E.164 format
    if (!phoneNumber.startsWith('+')) {
      setError('Phone number must be in E.164 format (e.g., +1234567890)');
      return;
    }

    setError('');
    setCallState('calling');
    setDuration(0);

    try {
      const call = await initiateOutboundCall(phoneNumber.trim());
      setActiveCall(call);
      setIsPolling(true);
      
      // Initial status will likely be 'initiated' or 'ringing'
      if (call.status === 'initiated' || call.status === 'ringing') {
        setCallState('calling');
      } else if (call.status === 'in-progress') {
        setCallState('in-progress');
      }
    } catch (err) {
      setCallState('error');
      setError(err instanceof Error ? err.message : 'Failed to initiate call');
    }
  };

  const handleEndCall = async () => {
    if (!activeCall?.call_id) return;

    try {
      await endCall(activeCall.call_id);
      setCallState('ended');
      setIsPolling(false);
    } catch (err) {
      console.error('Failed to end call:', err);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusText = () => {
    switch (callState) {
      case 'idle': return 'Ready to call';
      case 'calling': return 'Calling...';
      case 'in-progress': return `Call in progress (${formatDuration(duration)})`;
      case 'ended': return 'Call ended';
      case 'error': return 'Call failed';
      default: return '';
    }
  };

  const getStatusColor = () => {
    switch (callState) {
      case 'idle': return 'text-zinc-500';
      case 'calling': return 'text-blue-600';
      case 'in-progress': return 'text-green-600';
      case 'ended': return 'text-zinc-500';
      case 'error': return 'text-red-600';
      default: return 'text-zinc-500';
    }
  };

  return (
    <Shell>
      <div className="mb-6">
        <div className="text-2xl font-semibold">Phone Dialer</div>
        <div className="mt-1 text-sm text-zinc-600">
          Make outbound calls to phone numbers using your voice agent.
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Outbound Dialer */}
        <div className="rounded-xl border border-zinc-200 bg-white p-6">
          <div className="flex items-center gap-2 mb-4">
            <PhoneIcon />
            <h2 className="text-lg font-semibold">Outbound Call</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+1234567890"
                disabled={callState === 'calling' || callState === 'in-progress'}
                className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent disabled:bg-zinc-100 disabled:cursor-not-allowed"
              />
              <p className="mt-1 text-xs text-zinc-500">
                Enter number in E.164 format (with + and country code)
              </p>
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                {error}
              </div>
            )}

            <div className={`text-sm font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </div>

            <div className="flex gap-2">
              {(callState === 'idle' || callState === 'ended' || callState === 'error') && (
                <button
                  onClick={handleCall}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-colors font-medium"
                >
                  <PhoneIcon />
                  Call
                </button>
              )}

              {(callState === 'calling' || callState === 'in-progress') && (
                <button
                  onClick={handleEndCall}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  <CallEndIcon />
                  End Call
                </button>
              )}
            </div>

            {activeCall && (
              <div className="mt-4 p-3 bg-zinc-50 rounded-lg text-xs text-zinc-600">
                <div className="grid grid-cols-2 gap-2">
                  <div>Call ID:</div>
                  <div className="font-mono">{activeCall.call_id.slice(0, 8)}...</div>
                  <div>Twilio SID:</div>
                  <div className="font-mono">{activeCall.twilio_call_sid.slice(0, 12)}...</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="rounded-xl border border-zinc-200 bg-white p-6">
          <h2 className="text-lg font-semibold mb-4">How It Works</h2>
          <div className="space-y-3 text-sm text-zinc-600">
            <p>
              <strong className="text-zinc-900">1. Enter a phone number</strong> in E.164 format 
              (e.g., +1 for US numbers).
            </p>
            <p>
              <strong className="text-zinc-900">2. Click Call</strong> to initiate the outbound call.
            </p>
            <p>
              <strong className="text-zinc-900">3. Twilio dials</strong> the number and connects 
              to your Vapi AI assistant.
            </p>
            <p>
              <strong className="text-zinc-900">4. The AI agent</strong> handles the conversation 
              automatically.
            </p>
            <p>
              <strong className="text-zinc-900">5. Call ends</strong> when complete or when you click End.
            </p>
          </div>

          <div className="mt-6 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Note:</strong> You need to configure your Twilio phone number and 
              Vapi assistant in Settings before making calls.
            </p>
          </div>
        </div>
      </div>
    </Shell>
  );
}

export default withAuth(DialerPage);
