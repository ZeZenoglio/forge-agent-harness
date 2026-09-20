import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import { EventBubble } from './components/EventBubble';
import type { AgentEvent } from './components/EventBubble';
import { ApprovalGate } from './components/ApprovalGate';
import { ArtifactModal } from './components/ArtifactModal';
import type { ArtifactDetails } from './components/ArtifactModal';
import { ConversationSidebar } from './components/ConversationSidebar';
import type { ConversationSummary, SessionMetrics } from './components/ConversationSidebar';

/** Normalise an event from the backend. */
function normaliseEvent(raw: Record<string, unknown>): AgentEvent {
  const meta = (raw.metadata || {}) as AgentEvent['metadata'];
  return {
    type: (raw.type ?? raw.event_type ?? 'thought') as AgentEvent['type'],
    content: (raw.content ?? '') as string,
    tool_name: raw.tool_name as string | undefined,
    seq: raw.seq as number | undefined,
    id: raw.id as string | undefined,
    metadata: meta,
  };
}

function App() {
  const [task, setTask] = useState('');
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [metrics, setMetrics] = useState<SessionMetrics>({
    tokensUsed: 0,
    costUsd: 0,
    turns: 0,
    maxTurns: 10,
  });

  // Artifact modal state
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactDetails | null>(null);
  const [isArtifactModalOpen, setIsArtifactModalOpen] = useState(false);

  const eventsEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom as events arrive
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  // Load conversations list
  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/conversations');
      if (res.ok) {
        const json = (await res.json()) as { data: ConversationSummary[] };
        setConversations(json.data || []);
      }
    } catch (err) {
      console.error('Failed to load conversations', err);
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  // Connect to EventSource when sessionId is set
  useEffect(() => {
    if (!sessionId) return;
    const sse = new EventSource(`/api/v1/agent/stream/${sessionId}`);

    const handleMessage = (e: MessageEvent) => {
      try {
        const raw = JSON.parse(e.data) as Record<string, unknown>;
        const ev = normaliseEvent(raw);

        // Update real-time token metrics if provided
        if (ev.metadata?.tokens_used !== undefined) {
          setMetrics(prev => ({
            ...prev,
            tokensUsed: ev.metadata?.tokens_used || prev.tokensUsed,
            costUsd: ev.metadata?.cost_usd ?? prev.costUsd,
            turns: (ev.metadata?.iterations ?? prev.turns) + 1,
          }));
        }

        setEvents(prev => [...prev, ev]);

        if (ev.type === 'finish') {
          sse.close();
          setIsRunning(false);
          void loadConversations();
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
  }, [sessionId, loadConversations]);

  // Select and switch to an existing conversation
  const handleSelectConversation = async (convId: string) => {
    if (isRunning) return;
    setActiveConversationId(convId);
    setHasError(false);
    setSessionId(null);

    try {
      const res = await fetch(`/api/v1/conversations/${convId}`);
      if (res.ok) {
        const json = await res.json();
        const data = json.data as {
          messages?: Array<{ role: string; content: string }>;
        };

        if (data.messages && data.messages.length > 0) {
          const restoredEvents: AgentEvent[] = data.messages.map((m, idx) => ({
            type: m.role === 'user' ? 'user' : 'finish',
            content: m.content,
            seq: idx,
          }));
          setEvents(restoredEvents);
        } else {
          setEvents([]);
        }
      }
    } catch (err) {
      console.error('Failed to retrieve conversation history', err);
    }
  };

  // Start a new conversation
  const handleNewConversation = () => {
    if (isRunning) return;
    setActiveConversationId(null);
    setSessionId(null);
    setEvents([]);
    setHasError(false);
    setTask('');
    setMetrics({
      tokensUsed: 0,
      costUsd: 0,
      turns: 0,
      maxTurns: 10,
    });
    inputRef.current?.focus();
  };

  // Delete a conversation
  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`/api/v1/conversations/${convId}`, { method: 'DELETE' });
      if (activeConversationId === convId) {
        handleNewConversation();
      }
      void loadConversations();
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  // Submit prompt - continues current conversation if active
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim() || isRunning) return;

    const currentTask = task.trim();
    setTask('');
    setIsRunning(true);
    setHasError(false);

    // Append user turn to timeline
    setEvents(prev => [...prev, { type: 'user', content: currentTask }]);

    try {
      const res = await fetch('/api/v1/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: currentTask,
          conversation_id: activeConversationId || undefined,
          max_iterations: 10,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || res.statusText);
      }

      const json = (await res.json()) as {
        session_id: string;
        conversation_id: string;
      };

      if (!activeConversationId && json.conversation_id) {
        setActiveConversationId(json.conversation_id);
      }
      setSessionId(json.session_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setEvents(prev => [...prev, { type: 'error', content: msg }]);
      setIsRunning(false);
      setHasError(true);
    }
  };

  const hasApprovalRequest = events.some(e => e.type === 'approval_requested');
  const lastEvent = events.at(-1);

  return (
    <div className="app-container">
      {/* ── Left Sidebar ────────────────────────────────────────── */}
      <ConversationSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isRunning={isRunning}
        metrics={metrics}
      />

      {/* ── Main Chat Interface ─────────────────────────────────── */}
      <div className="main-panel">
        <header className="app-header glass-panel">
          <div>
            <h1 className="text-gradient">Agent Harness</h1>
            <p>JO Harness · Forge UI · Multi-Turn Agent Studio</p>
          </div>
          {lastEvent && (
            <div className="header-last-event muted">
              Status: <strong>{hasError ? 'Error' : isRunning ? 'Processing…' : 'Ready'}</strong>
            </div>
          )}
        </header>

        <main className="chat-interface glass-panel">
          <div className="events-timeline">
            {events.length === 0 && !isRunning && (
              <div className="empty-state">
                <span className="icon">⚡</span>
                <h2>Start an agent workflow</h2>
                <p>
                  Ask a research question, request a document or report, or execute tools.
                </p>
              </div>
            )}

            {events.map((ev, idx) => (
              <EventBubble
                key={idx}
                event={ev}
                onOpenArtifact={art => {
                  setSelectedArtifact(art);
                  setIsArtifactModalOpen(true);
                }}
              />
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
                <span>Agent is thinking and extracting sources…</span>
              </div>
            )}

            <div ref={eventsEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="task-input-form">
            <textarea
              ref={inputRef}
              id="task-input"
              value={task}
              onChange={e => setTask(e.target.value)}
              placeholder="Ask a question, follow up on the previous answer, or request a research document…"
              disabled={isRunning}
              rows={2}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit(e);
                }
              }}
            />
            <button id="run-agent-btn" type="submit" disabled={!task.trim() || isRunning}>
              {isRunning ? '⏳ Running…' : '▶ Send'}
            </button>
          </form>
        </main>
      </div>

      {/* ── Artifact Preview & Download Modal ────────────────────── */}
      <ArtifactModal
        isOpen={isArtifactModalOpen}
        artifact={selectedArtifact}
        onClose={() => setIsArtifactModalOpen(false)}
      />
    </div>
  );
}

export default App;
