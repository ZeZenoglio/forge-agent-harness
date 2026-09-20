import React from 'react';
import './EventBubble.css';

export interface AgentEvent {
  type: 'start' | 'thought' | 'tool_call' | 'tool_result' | 'approval_requested' | 'finish' | 'error';
  content: string;
  tool_name?: string;
  seq?: number;
  id?: string;
}

interface EventBubbleProps {
  event: AgentEvent;
}

export const EventBubble: React.FC<EventBubbleProps> = ({ event }) => {
  return (
    <div className={`event-bubble event-${event.type} glass-panel`}>
      <div className="event-header">
        <span className="event-type">
          {event.type.replace('_', ' ').toUpperCase()}
        </span>
        {event.tool_name && (
          <span className="event-tool">[{event.tool_name}]</span>
        )}
      </div>
      <div className="event-content">
        <pre>{event.content}</pre>
      </div>
    </div>
  );
};
