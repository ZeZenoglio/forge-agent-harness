import React, { useState } from 'react';
import './ApprovalGate.css';

interface ApprovalGateProps {
  sessionId: string;
  onApproved: () => void;
}

export const ApprovalGate: React.FC<ApprovalGateProps> = ({ sessionId, onApproved }) => {
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setIsApproving(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/agent/tasks/${sessionId}/approve`, {
        method: 'POST',
      });
      if (!res.ok) {
        throw new Error(`Failed to approve: ${res.statusText}`);
      }
      onApproved();
    } catch (err: any) {
      setError(err.message);
      setIsApproving(false);
    }
  };

  return (
    <div className="approval-gate glass-panel">
      <div className="approval-header">
        <span className="icon">⚠️</span>
        <h3>Human-in-the-Loop Approval Required</h3>
      </div>
      <p>The agent is attempting to execute a potentially dangerous or restricted action. Review the tool call above and approve to continue.</p>
      
      {error && <div className="error-msg">{error}</div>}
      
      <div className="approval-actions">
        <button onClick={handleApprove} disabled={isApproving}>
          {isApproving ? 'Approving...' : 'Approve Execution'}
        </button>
      </div>
    </div>
  );
};
