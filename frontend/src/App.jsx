import React, { useState, useEffect } from 'react'
import axios from 'axios'

// Используем VITE_API_URL (поддерживается Vite)
const API_URL = import.meta.env.VITE_API_URL || '/api'

const CHECK_TYPES = [
  { value: 'ping', label: 'Ping' },
  { value: 'http', label: 'HTTP' },
  { value: 'https', label: 'HTTPS' },
  { value: 'tcp', label: 'TCP Port' },
  { value: 'dns_a', label: 'DNS A' },
  { value: 'dns_aaaa', label: 'DNS AAAA' },
  { value: 'dns_mx', label: 'DNS MX' },
  { value: 'dns_ns', label: 'DNS NS' },
  { value: 'dns_txt', label: 'DNS TXT' }
]

const PRESETS = {
  quick: ['ping', 'http'],
  full: ['ping', 'http', 'https', 'dns_a', 'dns_mx'],
  dns: ['dns_a', 'dns_aaaa', 'dns_mx', 'dns_ns', 'dns_txt']
}

function App() {
  const [target, setTarget] = useState('')
  const [selectedChecks, setSelectedChecks] = useState(PRESETS.quick)
  const [currentCheck, setCurrentCheck] = useState(null)
  const [checksHistory, setChecksHistory] = useState([])
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(false)

  // Загрузка темы из localStorage
  useEffect(() => {
    const saved = localStorage.getItem('darkMode') === 'true'
    setDarkMode(saved)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
    localStorage.setItem('darkMode', darkMode)
  }, [darkMode])

  // Загрузка данных
  const loadChecksHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/checks/`)
      setChecksHistory(response.data.slice(0, 10))
    } catch (error) {
      console.error('Error loading checks history:', error)
    }
  }

  const loadAgents = async () => {
    try {
      const response = await axios.get(`${API_URL}/agents/`)
      setAgents(response.data)
    } catch (error) {
      console.error('Error loading agents:', error)
    }
  }

  // Автообновление каждые 10 секунд
  useEffect(() => {
    loadChecksHistory()
    loadAgents()
    const interval = setInterval(() => {
      loadChecksHistory()
      loadAgents()
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleCheckboxChange = (checkType) => {
    setSelectedChecks(prev =>
      prev.includes(checkType)
        ? prev.filter(type => type !== checkType)
        : [...prev, checkType]
    )
  }

  const applyPreset = (preset) => {
    setSelectedChecks([...PRESETS[preset]])
  }

  const runCheck = async (e) => {
    e.preventDefault()
    if (!target || selectedChecks.length === 0) return
    setLoading(true)
    try {
      const response = await axios.post(`${API_URL}/checks/`, {
        target,
        check_types: selectedChecks
      })
      const newCheck = response.data
      setCurrentCheck(newCheck)
      // Добавляем в историю сразу (даже если pending)
      setChecksHistory(prev => [newCheck, ...prev.slice(0, 9)])

      // Опрос результата
      const checkInterval = setInterval(async () => {
        try {
          const resultResponse = await axios.get(`${API_URL}/checks/${newCheck.id}`)
          const updatedCheck = resultResponse.data
          if (updatedCheck.status === 'completed') {
            setCurrentCheck(updatedCheck)
            // Обновляем в истории
            setChecksHistory(prev =>
              prev.map(c => (c.id === updatedCheck.id ? updatedCheck : c))
            )
            clearInterval(checkInterval)
          }
        } catch (error) {
          console.error('Polling error:', error)
        }
      }, 2000)

      setLoading(false)
    } catch (error) {
      console.error('Error running check:', error)
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🌐 Host Checker</h1>
        <p>Diagnose connectivity & DNS from multiple locations</p>
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="theme-toggle"
          aria-label="Toggle theme"
        >
          {darkMode ? '☀️' : '🌙'}
        </button>
      </div>

      <div className="card">
        <h2>New Diagnostic Check</h2>
        <div className="presets">
          <button onClick={() => applyPreset('quick')} className="preset-btn">⚡ Quick</button>
          <button onClick={() => applyPreset('full')} className="preset-btn">🔍 Full</button>
          <button onClick={() => applyPreset('dns')} className="preset-btn">📡 DNS Only</button>
        </div>
        <form onSubmit={runCheck}>
          <div className="form-group">
            <label htmlFor="target">Target (e.g. google.com or 8.8.8.8)</label>
            <input
              type="text"
              id="target"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Enter hostname or IP"
              required
            />
          </div>
          <div className="form-group">
            <label>Check Types</label>
            <div className="checkbox-grid">
              {CHECK_TYPES.map(type => (
                <label key={type.value} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedChecks.includes(type.value)}
                    onChange={() => handleCheckboxChange(type.value)}
                  />
                  <span>{type.label}</span>
                </label>
              ))}
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Running Checks…' : 'Run Diagnostic'}
          </button>
        </form>
      </div>

      {currentCheck && (
        <div className="card">
          <h2>Current Results</h2>
          <div className="results-grid">
            {currentCheck.results?.map(result => (
              <div
                key={result.id || result.check_type}
                className={`result-card ${result.success ? 'success' : 'error'}`}
              >
                <div className="result-header">
                  <strong>{result.check_type.toUpperCase()}</strong>
                  <span className={`status-badge ${result.success ? 'success' : 'error'}`}>
                    {result.success ? '✅' : '❌'}
                  </span>
                </div>
                {result.response_time && (
                  <div className="metric">⏱️ {result.response_time} ms</div>
                )}
                {result.agent_name && (
                  <div className="agent">🤖 {result.agent_name}</div>
                )}
                {/* Детали */}
                {result.check_type === 'http' && result.result_data?.status_code && (
                  <div className="detail">
                    HTTP {result.result_data.status_code} | {result.result_data.content_length} bytes
                  </div>
                )}
                {result.check_type.startsWith('dns') && result.result_data?.records && (
                  <div className="detail">
                    {result.result_data.records.map((r, i) => (
                      <div key={i}>{r}</div>
                    ))}
                  </div>
                )}
                {result.check_type === 'tcp' && (
                  <div className="detail">
                    Port {result.result_data?.port} is {result.result_data?.status}
                  </div>
                )}
                {result.error_message && (
                  <div className="error-detail">⚠️ {result.error_message}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Active Agents ({agents.length})</h2>
        <div className="agents-list">
          {agents.map(agent => (
            <div key={agent.id} className="agent-item">
              <div className={`agent-status-dot ${agent.is_active ? 'online' : 'offline'}`}></div>
              <div>
                <div className="agent-name">{agent.name}</div>
                <div className="agent-meta">
                  {agent.location || 'Unknown location'} •
                  Last: {agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleTimeString() : 'Never'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Recent Checks ({checksHistory.length})</h2>
        <div className="history-list">
          {checksHistory.length === 0 ? (
            <p className="empty-state">No checks yet. Run your first diagnostic!</p>
          ) : (
            checksHistory.map(check => (
              <div key={check.id} className="history-item">
                <div>
                  <strong>{check.target}</strong>
                  <div className="check-types">{check.check_types.join(', ')}</div>
                </div>
                <div className="history-meta">
                  <span className={`status ${check.status}`}>{check.status}</span>
                  <time>{new Date(check.created_at).toLocaleString()}</time>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default App