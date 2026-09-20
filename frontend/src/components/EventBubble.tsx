import React, { useState } from 'react';
import './EventBubble.css';
import type { ArtifactDetails } from './ArtifactModal';

export interface AgentEvent {
  type:
    | 'start'
    | 'thought'
    | 'tool_call'
    | 'tool_result'
    | 'approval_requested'
    | 'finish'
    | 'error'
    | 'user';
  content: string;
  tool_name?: string;
  seq?: number;
  id?: string;
  metadata?: {
    tokens_used?: number;
    cost_usd?: number;
    iterations?: number;
    conversation_id?: string;
    artifact_id?: string;
    artifact_name?: string;
    artifact_url?: string;
  };
}

const EVENT_META: Record<AgentEvent['type'], { icon: string; title: string }> = {
  user: { icon: '👤', title: 'User Request' },
  start: { icon: '▶', title: 'Task Initialized' },
  thought: { icon: '🧠', title: 'Reasoning & Planning' },
  tool_call: { icon: '🔧', title: 'Tool Execution' },
  tool_result: { icon: '📋', title: 'Tool Observation' },
  approval_requested: { icon: '⚠️', title: 'Human Approval Required' },
  finish: { icon: '✅', title: 'Final Answer' },
  error: { icon: '❌', title: 'Error Encountered' },
};

interface EventBubbleProps {
  event: AgentEvent;
  onOpenArtifact?: (artifact: ArtifactDetails) => void;
}

/**
 * Format markdown text with headers, lists, links, and bold text without third-party heavy dependencies.
 */
function renderSimpleMarkdown(text: string) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    // Headers
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={lineIdx} className="md-h3">
          {trimmed.slice(4)}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={lineIdx} className="md-h2">
          {trimmed.slice(3)}
        </h2>
      );
      return;
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={lineIdx} className="md-h1">
          {trimmed.slice(2)}
        </h1>
      );
      return;
    }

    // List item
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <li key={lineIdx} className="md-li">
          {formatInline(trimmed.slice(2))}
        </li>
      );
      return;
    }

    // Numbered list item
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <li key={lineIdx} className="md-li-num" value={numMatch[1]}>
          <span className="md-num-prefix">{numMatch[1]}.</span>{' '}
          {formatInline(numMatch[2])}
        </li>
      );
      return;
    }

    // Empty line
    if (!trimmed) {
      elements.push(<div key={lineIdx} className="md-spacer" />);
      return;
    }

    // Standard paragraph
    elements.push(
      <p key={lineIdx} className="md-p">
        {formatInline(trimmed)}
      </p>
    );
  });

  return elements;
}

/** Format inline markdown: links and bold text */
function formatInline(text: string): React.ReactNode[] {
  // Regex for [link text](url) and **bold text**
  const regex = /(\[.*?\]\(.*?\)|\*\*.*?\*\*)/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    // Markdown link: [Title](https://...)
    const linkMatch = part.match(/^\[(.*?)\]\((.*?)\)$/);
    if (linkMatch) {
      return (
        <a
          key={idx}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="md-link"
        >
          {linkMatch[1]}
        </a>
      );
    }

    // Bold: **text**
    const boldMatch = part.match(/^\*\*(.*?)\*\*$/);
    if (boldMatch) {
      return (
        <strong key={idx} className="md-bold">
          {boldMatch[1]}
        </strong>
      );
    }

    return part;
  });
}

/** Extract preview line for collapsed header */
function getPreviewSnippet(content: string): string {
  const firstLine = content.split('\n').find(l => l.trim().length > 0) || '';
  const cleaned = firstLine.replace(/^[#\-*>\s]+/, '').trim();
  if (cleaned.length > 75) {
    return cleaned.slice(0, 75) + '…';
  }
  return cleaned;
}

export const EventBubble: React.FC<EventBubbleProps> = ({
  event,
  onOpenArtifact,
}) => {
  // Collapse thoughts, start, and tool results by default to keep chat clean
  // Always expand 'finish' and 'user' turns
  const defaultExpanded =
    event.type === 'finish' || event.type === 'user' || event.type === 'error';

  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  const meta = EVENT_META[event.type] ?? { icon: '●', title: event.type };

  // Detect artifact from metadata or content
  let artifactId = event.metadata?.artifact_id;
  let artifactName = event.metadata?.artifact_name;

  if (!artifactName && event.content.includes('research_')) {
    const match = event.content.match(/research_[a-zA-Z0-9_-]+\.md/);
    if (match) {
      artifactName = match[0];
    }
  }

  const preview = getPreviewSnippet(event.content);

  return (
    <div
      className={`event-card event-${event.type} ${
        isExpanded ? 'card-expanded' : 'card-collapsed'
      }`}
    >
      {/* ── Collapsible Header Row ──────────────────────────────────── */}
      <div
        className="card-header"
        onClick={() => setIsExpanded(prev => !prev)}
        title={isExpanded ? 'Click to collapse' : 'Click to expand'}
        role="button"
        tabIndex={0}
      >
        <span className="card-icon" role="img" aria-label={meta.title}>
          {meta.icon}
        </span>

        <span className="card-title">
          {meta.title}
          {event.tool_name && (
            <span className="card-tool-chip">{event.tool_name}</span>
          )}
        </span>

        {!isExpanded && preview && (
          <span className="card-preview-snippet">{preview}</span>
        )}

        <div className="card-header-right">
          {event.seq !== undefined && (
            <span className="card-seq">#{event.seq}</span>
          )}
          <span className="card-chevron">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {/* ── Collapsible Content Body ─────────────────────────────────── */}
      {isExpanded && (
        <div className="card-body">
          {event.type === 'finish' || event.type === 'tool_result' ? (
            <div className="formatted-markdown">
              {renderSimpleMarkdown(event.content)}
            </div>
          ) : (
            <pre className="raw-content">{event.content}</pre>
          )}

          {/* Interactive Artifact Card if present */}
          {artifactName && (
            <div className="artifact-banner">
              <div className="artifact-banner-left">
                <span className="artifact-banner-icon">📄</span>
                <div>
                  <div className="artifact-banner-name">{artifactName}</div>
                  <div className="artifact-banner-sub">
                    Markdown research document saved to registry
                  </div>
                </div>
              </div>
              <div className="artifact-banner-actions">
                {onOpenArtifact && (
                  <button
                    className="artifact-btn preview-btn"
                    onClick={e => {
                      e.stopPropagation();
                      onOpenArtifact({
                        id: artifactId || '',
                        name: artifactName || 'research_document.md',
                        content:
                          event.type === 'tool_result'
                            ? event.content
                            : undefined,
                      });
                    }}
                  >
                    👁 Preview Artifact
                  </button>
                )}
                {artifactId && (
                  <a
                    href={`/api/v1/artifacts/${artifactId}/download`}
                    download={artifactName}
                    className="artifact-btn download-btn"
                    onClick={e => e.stopPropagation()}
                  >
                    ⬇ Download
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
