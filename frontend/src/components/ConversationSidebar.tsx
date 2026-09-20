import React from 'react';
import './ConversationSidebar.css';

export interface ConversationSummary {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface SessionMetrics {
  tokensUsed: number;
  costUsd: number;
  turns: number;
  maxTurns: number;
}

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string, e: React.MouseEvent) => void;
  isRunning: boolean;
  metrics: SessionMetrics;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isRunning,
  metrics,
}) => {
  return (
    <aside className="conversations-sidebar glass-panel">
      {/* ── Brand ─────────────────────────────────────────────────── */}
      <div className="sidebar-brand-row">
        <div className="sidebar-brand-title">
          <span style={{ fontSize: '20px' }}>⚡</span>
          <span className="text-gradient">Forge Agent</span>
        </div>
      </div>

      {/* ── New Chat Button ───────────────────────────────────────── */}
      <button
        className="new-chat-btn"
        onClick={onNewConversation}
        disabled={isRunning}
        title="Start a new conversation"
      >
        <span>+</span> New Chat
      </button>

      {/* ── History Section ───────────────────────────────────────── */}
      <div className="sidebar-section-title">Recent Chats</div>

      <ul className="conversation-list">
        {conversations.length === 0 ? (
          <li className="conv-empty">No previous chats</li>
        ) : (
          conversations.map(conv => (
            <li
              key={conv.id}
              className={`conversation-item ${
                conv.id === activeConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conv-title-wrapper">
                <span className="conv-icon">💬</span>
                <span className="conv-title" title={conv.title}>
                  {conv.title || 'Untitled Chat'}
                </span>
              </div>
              <button
                className="conv-delete-btn"
                onClick={e => onDeleteConversation(conv.id, e)}
                title="Delete chat"
              >
                🗑
              </button>
            </li>
          ))
        )}
      </ul>

      {/* ── Token & Cost Consumption Widget ───────────────────────── */}
      <div className="sidebar-metrics-card">
        <div className="metrics-header">
          <span>Session Budget</span>
          <span
            style={{
              color: isRunning ? '#34d399' : '#94a3b8',
              fontSize: '10px',
            }}
          >
            ● {isRunning ? 'Running' : 'Idle'}
          </span>
        </div>

        <div className="metrics-grid">
          <div className="metric-item">
            <span className="metric-label">Tokens</span>
            <span className="metric-value">
              {metrics.tokensUsed.toLocaleString()}
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Est. Cost</span>
            <span className="metric-value">
              ${metrics.costUsd.toFixed(4)}
            </span>
          </div>
          <div className="metric-item" style={{ gridColumn: 'span 2' }}>
            <span className="metric-label">Execution Turns</span>
            <span className="metric-value">
              {metrics.turns} / {metrics.maxTurns}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
