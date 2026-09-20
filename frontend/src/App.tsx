import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { EventBubble } from './components/EventBubble';
import type { AgentEvent } from './components/EventBubble';
import { ApprovalGate } from './components/ApprovalGate';

/** Normalise an event from the backend.
 *
 * The backend emits ``event_type`` but the frontend interface uses ``type``.
 * This shim handles both shapes so we are resilient to either.
 */
function normaliseEvent(raw: Record<string, unknown>): AgentEvent {
  return {
    type: (raw.type ?? raw.event_type ?? 'thought') as AgentEvent['type'],
    content: (raw.content ?? '') as string,
    tool_name: raw.tool_name as string | undefined,
    seq: raw.seq as number | undefined,
    id: raw.id as string | undefined,
  };
}

function StatusBadge({ isRunning, hasError }: { isRunning: boolean; hasError: boolean }) {
  if (hasError) return <span className="status-badge status-error">● Error</span>;
  if (isRunning) return <span className="status-badge status-running">● Running</span>;
  return <span className="status-badge status-idle">● Idle</span>;
}

function App() {
  const [task, setTask] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [hasError, setHasError] = useState(false);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  // Connect to EventSource when sessionId is set
  useEffect(() => {
    if (!sessionId) return;
    const sse = new EventSource(`/api/v1/agent/stream/${sessionId}`);

    const handleMessage = (e: MessageEvent) => {
      try {
        const raw = JSON.parse(e.data) as Record<string, unknown>;
        const ev = normaliseEvent(raw);
        setEvents(prev => [...prev, ev]);

        if (ev.type === 'finish') {
          sse.close();
          setIsRunning(false);
        }
        if (ev.type === 'error') {
          sse.close();
          setIsRunning(false);
          setHasError(true);
        }
      } catch (err) {
        console.error('Failed to parse SSE data', err);
      }
    };

    sse.onmessage = handleMessage;

    sse.onerror = () => {
      sse.close();
      setIsRunning(false);
      setHasError(true);
      setEvents(prev => [
        ...prev,
        { type: 'error', content: 'Connection to agent stream lost.' },
      ]);
    };

    return () => sse.close();
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim() || isRunning) return;

    setEvents([]);
    setSessionId(null);
    setIsRunning(true);
    setHasError(false);

    try {
      const res = await fetch('/api/v1/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, max_iterations: 10 }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || res.statusText);
      }

      const data = await res.json() as { session_id: string };
      setSessionId(data.session_id);
      setTask('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setEvents([{ type: 'error', content: msg }]);
      setIsRunning(false);
      setHasError(true);
    }
  };

  const handleReset = () => {
    setEvents([]);
    setSessionId(null);
    setIsRunning(false);
    setHasError(false);
    setTask('');
  };

  const hasApprovalRequest = events.some(e => e.type === 'approval_requested');
  const lastEvent = events.at(-1);

  return (
    <div className="app-container">
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-brand">
          <span className="brand-icon">⚡</span>
          <span className="brand-name text-gradient">Forge</span>
        </div>

        <nav className="sidebar-nav">
          <p className="sidebar-label">Session</p>
          {sessionId ? (
            <code className="session-id">{sessionId.slice(0, 8)}…</code>
          ) : (
            <span className="session-id muted">—</span>
          )}

          <p className="sidebar-label" style={{ marginTop: '24px' }}>Status</p>
          <StatusBadge isRunning={isRunning} hasError={hasError} />

          <p className="sidebar-label" style={{ marginTop: '24px' }}>Events</p>
          <span className="event-count">{events.length}</span>
        </nav>

        <button
          className="reset-btn"
          onClick={handleReset}
          disabled={isRunning}
          title="Clear session"
        >
          ↺ New Session
        </button>
      </aside>

      {/* ── Main panel ──────────────────────────────────────────── */}
      <div className="main-panel">
        <header className="app-header glass-panel">
          <div>
            <h1 className="text-gradient">Agent Harness</h1>
            <p>JO Harness · Forge UI</p>
          </div>
          {lastEvent && (
            <div className="header-last-event muted">
              Last: <strong>{lastEvent.type.replace('_', ' ')}</strong>
            </div>
          )}
        </header>

        <main className="chat-interface glass-panel">
          <div className="events-timeline">
            {events.length === 0 && !isRunning && (
              <div className="empty-state">
                <span className="icon">🚀</span>
                <h2>Ready for your command</h2>
                <p>Enter a task below to awaken the agent.</p>
              </div>
            )}

            {events.map((ev, idx) => (
              <EventBubble key={idx} event={ev} />
            ))}

            {hasApprovalRequest && isRunning && (
              <ApprovalGate
                sessionId={sessionId!}
                onApproved={() => {
                  setEvents(prev => [
                    ...prev,
                    { type: 'start', content: '✅ Approval granted. Resuming execution…' },
                  ]);
                }}
              />
            )}

            {isRunning && !hasApprovalRequest && (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Agent is thinking…</span>
              </div>
            )}

            <div ref={eventsEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="task-input-form">
            <textarea
              id="task-input"
              value={task}
              onChange={e => setTask(e.target.value)}
              placeholder="E.g. Analyse the project directory and summarise the main components…"
              disabled={isRunning}
              rows={3}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit(e);
                }
              }}
            />
            <button id="run-agent-btn" type="submit" disabled={!task.trim() || isRunning}>
              {isRunning ? '⏳ Running…' : '▶ Run Agent'}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

export default App;
