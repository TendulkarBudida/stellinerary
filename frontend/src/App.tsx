import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState<string>('Loading...')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => {
        if (!res.ok) throw new Error('Network response was not ok')
        return res.json()
      })
      .then(data => {
        if (data.status === 'ok') {
          setHealthStatus('OK')
        } else {
          setHealthStatus('ERROR: ' + JSON.stringify(data))
        }
      })
      .catch(err => {
        setHealthStatus('ERROR: ' + err.message)
      })
  }, [])

  return (
    <div className="App dark-theme">
      <header className="header">
        <h1>✨ Stellinerary</h1>
        <p className="subtitle">Night Sky Expedition Orchestrator</p>
      </header>
      <main className="content">
        <div className="status-card">
          <h2>System Status</h2>
          <p>Backend: <strong>{healthStatus}</strong></p>
        </div>
      </main>
    </div>
  )
}

export default App
