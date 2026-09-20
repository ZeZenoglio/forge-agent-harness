import { useState } from 'react';
import { TaskInput } from './components/TaskInput';
import { EventLog } from './components/EventLog';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleStartSession = (id: string) => {
    setSessionId(id);
  };

  return (
    <div style={{ padding: 'var(--spacing-xl)', width: '100%' }}>
      <header style={{ textAlign: 'center', marginBottom: 'var(--spacing-xl)' }}>
        <h1 style={{ 
          fontSize: '3rem', 
          fontWeight: 600, 
          background: 'linear-gradient(to right, var(--primary), var(--accent))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: 'var(--spacing-sm)'
        }}>
          Forge
        </h1>
        <p style={{ color: 'var(--text-muted)' }}>Autonomous AI Agent Harness</p>
      </header>
      
      <main>
        <TaskInput onStartSession={handleStartSession} />
        {sessionId && <EventLog key={sessionId} sessionId={sessionId} />}
      </main>
    </div>
  );
}

export default App;
