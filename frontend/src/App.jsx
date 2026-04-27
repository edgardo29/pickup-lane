import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState({
    loading: true,
    error: '',
    data: null,
  })
  const [dbStatus, setDbStatus] = useState({
    loading: true,
    error: '',
    data: null,
  })

  useEffect(() => {
    const apiBaseUrl = 'http://127.0.0.1:8000'

    async function loadStatus(path, setter) {
      setter({ loading: true, error: '', data: null })

      try {
        const response = await fetch(`${apiBaseUrl}${path}`)

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }

        const data = await response.json()
        setter({ loading: false, error: '', data })
      } catch (error) {
        setter({
          loading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
          data: null,
        })
      }
    }

    loadStatus('/', setApiStatus)
    loadStatus('/db-health', setDbStatus)
  }, [])

  return (
    <main className="app-shell">
      <section className="status-panel">
        <p className="eyebrow">Pickup Lane</p>
        <h1>Local stack status</h1>
        <p className="intro">
          This frontend is calling the FastAPI backend directly and checking that
          the backend can also reach PostgreSQL.
        </p>

        <div className="status-grid">
          <StatusCard title="Backend API" endpoint="GET /" status={apiStatus} />
          <StatusCard
            title="Database Connection"
            endpoint="GET /db-health"
            status={dbStatus}
          />
        </div>
      </section>
    </main>
  )
}

function StatusCard({ title, endpoint, status }) {
  let stateLabel = 'Checking...'
  let toneClass = 'pending'

  if (status.error) {
    stateLabel = 'Connection failed'
    toneClass = 'error'
  } else if (status.data) {
    stateLabel = 'Connected'
    toneClass = 'success'
  }

  return (
    <article className={`status-card ${toneClass}`}>
      <div className="status-head">
        <div>
          <p className="card-label">{title}</p>
          <p className="endpoint">{endpoint}</p>
        </div>
        <span className="badge">{stateLabel}</span>
      </div>

      <div className="card-body">
        {status.loading && <p>Waiting for a response from the local service.</p>}
        {status.error && <p>{status.error}</p>}
        {status.data && <p>{status.data.message}</p>}
      </div>
    </article>
  )
}

export default App
