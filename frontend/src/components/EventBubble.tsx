import React from 'react';
import './EventBubble.css';

export interface AgentEvent {
  type: 'start' | 'thought' | 'tool_call' | 'tool_result' | 'approval_requested' | 'finish' | 'error';
  content: string;
  tool_name?: string;
  seq?: number;
  id?: string;
}

const EVENT_META: Record<AgentEvent['type'], { icon: string; label: string }> = {
  start:             { icon: '▶', label: 'Start' },
  thought:           { icon: '🧠', label: 'Thought' },
  tool_call:         { icon: '🔧', label: 'Tool Call' },
  tool_result:       { icon: '📋', label: 'Tool Result' },
  approval_requested:{ icon: '⚠️', label: 'Approval Required' },
  finish:            { icon: '✅', label: 'Finished' },
  error:             { icon: '❌', label: 'Error' },
};

interface EventBubbleProps {
  event: AgentEvent;
}

export const EventBubble: React.FC<EventBubbleProps> = ({ event }) => {
  const meta = EVENT_META[event.type] ?? { icon: '●', label: event.type };

  return (
    <div className={`event-bubble event-${event.type}`}>
      <div className="event-header">
        <span className="event-icon" role="img" aria-label={meta.label}>
          {meta.icon}
        </span>
        <span className="event-type-label">{meta.label}</span>
        {event.tool_name && (
          <span className="event-tool-chip">{event.tool_name}</span>
        )}
        {event.seq !== undefined && (
          <span className="event-seq">#{event.seq}</span>
        )}
      </div>
      <div className="event-content">
        <pre>{event.content}</pre>
      </div>
    </div>
  );
};
