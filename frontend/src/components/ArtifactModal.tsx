import React, { useState, useEffect } from 'react';
import './ArtifactModal.css';

export interface ArtifactDetails {
  id: string;
  name: string;
  mime_type?: string;
  size_bytes?: number;
  content?: string;
}

interface ArtifactModalProps {
  isOpen: boolean;
  artifact: ArtifactDetails | null;
  onClose: () => void;
}

export const ArtifactModal: React.FC<ArtifactModalProps> = ({
  isOpen,
  artifact,
  onClose,
}) => {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen || !artifact) return;

    // Close on Escape key
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);

    if (artifact.content) {
      setContent(artifact.content);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }

    if (artifact.id) {
      setLoading(true);
      fetch(`/api/v1/artifacts/${artifact.id}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.data && typeof data.data.content === 'string') {
            setContent(data.data.content);
          } else {
            setContent('(No preview available for this artifact)');
          }
        })
        .catch(err => {
          console.error('Failed to load artifact', err);
          setContent('(Error loading artifact content)');
        })
        .finally(() => setLoading(false));
    }

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, artifact, onClose]);

  if (!isOpen || !artifact) return null;

  const handleCopy = () => {
    void navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadUrl = `/api/v1/artifacts/${artifact.id}/download`;

  return (
    <div className="artifact-modal-backdrop" onClick={onClose}>
      <div
        className="artifact-modal-container"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="artifact-modal-title"
      >
        <div className="artifact-modal-header">
          <div className="artifact-modal-title">
            <span className="artifact-file-icon">📄</span>
            <div>
              <div id="artifact-modal-title" className="artifact-name">
                {artifact.name}
              </div>
            </div>
            {artifact.mime_type && (
              <span className="artifact-meta-pill">{artifact.mime_type}</span>
            )}
          </div>

          <div className="artifact-modal-actions">
            <button
              className="artifact-action-btn"
              onClick={handleCopy}
              title="Copy to clipboard"
            >
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
            <a
              href={downloadUrl}
              download={artifact.name}
              className="artifact-action-btn"
              title="Download file"
            >
              ⬇ Download
            </a>
            <button
              className="artifact-close-btn"
              onClick={onClose}
              title="Close modal"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="artifact-modal-body">
          {loading ? (
            <div className="artifact-loading">
              <span>Loading artifact content…</span>
            </div>
          ) : (
            <pre className="artifact-code-view">{content}</pre>
          )}
        </div>
      </div>
    </div>
  );
};
