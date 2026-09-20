import { useState } from 'react';
import './TaskInput.css';

interface TaskInputProps {
  onStartSession: (sessionId: string) => void;
}

export const TaskInput = ({ onStartSession }: TaskInputProps) => {
  const [task, setTask] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim()) return;

    setIsLoading(true);
    try {
      // Send the task to our backend API
      const response = await fetch('http://localhost:8000/api/v1/agent/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to start session');
      }
      
      const data = await response.json();
      onStartSession(data.session_id);
    } catch (error) {
      console.error("Error starting task:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="task-input-container animate-fade-in glass-panel">
      <form onSubmit={handleSubmit} className="task-input-form">
        <input
          type="text"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="What do you want Forge to do?"
          className="task-input"
          disabled={isLoading}
        />
        <button 
          type="submit" 
          className={`submit-button ${isLoading ? 'loading' : ''}`}
          disabled={isLoading || !task.trim()}
        >
          {isLoading ? 'Starting...' : 'Forge'}
        </button>
      </form>
    </div>
  );
};
