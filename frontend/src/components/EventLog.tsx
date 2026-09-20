import { useEffect, useState, useRef } from 'react';
import './EventLog.css';

interface AgentEvent {
  seq: number;
  event_type: string;
  content: string;
}

interface EventLogProps {
  sessionId: string;
}

export const EventLog = ({ sessionId }: EventLogProps) => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;


    const eventSource = new EventSource(`http://localhost:8000/api/v1/agent/stream/${sessionId}`);

    eventSource.onmessage = (event) => {
      try {
        const parsedEvent: AgentEvent = JSON.parse(event.data);
        setEvents((prev) => {
          // Prevent duplicates by checking seq
          if (prev.some(e => e.seq === parsedEvent.seq)) {
            return prev;
          }
          return [...prev, parsedEvent].sort((a, b) => a.seq - b.seq);
        });
      } catch (err) {
        console.error("Failed to parse event", err);
      }
    };

    eventSource.onerror = (error) => {
      console.error("EventSource failed:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  useEffect(() => {
    // Auto-scroll to bottom
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const getEventIcon = (type: string) => {
    switch(type) {
      case 'start': return '🚀';
      case 'tool_result': return '🔧';
      case 'finish': return '✅';
      default: return '💬';
    }
  };

  if (!sessionId) {
    return null;
  }

  return (
    <div className="event-log-container glass-panel animate-fade-in">
      <div className="event-log-header">
        <h3>Session: <span className="session-id">{sessionId.substring(0, 8)}...</span></h3>
        <div className="status-indicator animate-pulse"></div>
      </div>
      
      <div className="event-list">
        {events.length === 0 ? (
          <div className="empty-state">Waiting for events...</div>
        ) : (
          events.map((evt) => (
            <div key={evt.seq} className="event-item animate-fade-in">
              <div className="event-icon">{getEventIcon(evt.event_type)}</div>
              <div className="event-content">
                <span className="event-type">{evt.event_type}</span>
                <pre className="event-text">{evt.content}</pre>
              </div>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};
