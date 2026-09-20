import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { EventBubble } from './components/EventBubble';
import type { AgentEvent } from './components/EventBubble';
import { ApprovalGate } from './components/ApprovalGate';

function App() {
  const [task, setTask] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  // Connect to EventSource when sessionId is set
  useEffect(() => {
    if (!sessionId) return;
    const sse = new EventSource(`/api/v1/agent/stream/${sessionId}`);

    const handleMessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as AgentEvent;
        setEvents(prev => [...prev, data]);
        
        if (data.type === 'finish' || data.type === 'error') {
          sse.close();
          setIsRunning(false);
        }
      } catch (err) {
        console.error('Failed to parse SSE data', err);
      }
    };

    sse.onmessage = handleMessage;
    
    sse.onerror = (e) => {
      console.error('SSE Error', e);
      sse.close();
      setIsRunning(false);
      setEvents(prev => [...prev, { type: 'error', content: 'Event stream connection lost.' }]);
    };

    return () => {
      sse.close();
    };
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim() || isRunning) return;

    setEvents([]);
    setSessionId(null);
    setIsRunning(true);

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

      const data = await res.json();
      setSessionId(data.session_id);
      setTask('');
    } catch (err: any) {
      setEvents([{ type: 'error', content: err.message }]);
      setIsRunning(false);
    }
  };

  const hasApprovalRequest = events.some(e => e.type === 'approval_requested');

  return (
    <div className="app-container">
      <header className="app-header glass-panel">
        <h1 className="text-gradient">Forge UI</h1>
        <p>Agent Harness Interface</p>
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
                 setEvents(prev => [...prev, { type: 'start', content: 'Approval granted. Resuming execution...' }]);
               }} 
             />
          )}

          {isRunning && !hasApprovalRequest && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <span>Agent is thinking...</span>
            </div>
          )}
          
          <div ref={eventsEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="task-input-form">
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="E.g. Analyze the current directory and list the files..."
            disabled={isRunning}
            rows={3}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button type="submit" disabled={!task.trim() || isRunning}>
            {isRunning ? 'Running...' : 'Run Agent'}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
