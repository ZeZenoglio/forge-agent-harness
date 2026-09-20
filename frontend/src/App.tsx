import React from 'react'
import './index.css'

function App() {
  return (
    <div className="layout-container">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.025em' }}>Forge</h1>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Agents</span>
          <span style={{ color: 'var(--text-muted)' }}>Settings</span>
        </nav>
      </header>
      
      <main className="glass-panel" style={{ padding: '3rem', minHeight: '60vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
        <div style={{ maxWidth: '600px' }}>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 600, marginBottom: '1rem', background: 'linear-gradient(to right, #818cf8, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Agent Workspace
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', marginBottom: '2.5rem', lineHeight: 1.6 }}>
            Forge is a modular, model-agnostic platform. Connect your models, configure guardrails, and stream agent executions in real-time.
          </p>
          <button className="btn-primary">Initialize Agent</button>
        </div>
      </main>
    </div>
  )
}

export default App
