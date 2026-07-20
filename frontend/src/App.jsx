import { useEffect, useState } from 'react'
import axios from 'axios'

/**
 * App
 *
 * Module 1 responsibility only: prove that the full chain
 * (React -> Vite dev proxy -> FastAPI -> SQLite) is wired correctly.
 *
 * The claim-filing UI itself is built in later modules (Module 3 onward).
 * This component is intentionally small but fully functional: it makes
 * a real network call and renders real state, it does not fake a result.
 */
function App() {
  const [status, setStatus] = useState('checking')
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function checkBackend() {
      try {
        const response = await axios.get('/api/health')
        if (!cancelled) {
          setStatus('connected')
          setDetail(response.data)
        }
      } catch (err) {
        if (!cancelled) {
          setStatus('error')
          setError(
            err.response
              ? `Backend responded with ${err.response.status}`
              : 'Could not reach backend. Is uvicorn running on port 8000?'
          )
        }
      }
    }

    checkBackend()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <h1 className="text-xl font-semibold text-slate-900">
          FasalBima Pramaan
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Module 1 — Project Setup Check
        </p>

        <div className="mt-6 flex items-center gap-3">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              status === 'connected'
                ? 'bg-emerald-500'
                : status === 'error'
                ? 'bg-red-500'
                : 'bg-amber-400 animate-pulse'
            }`}
          />
          <span className="text-sm font-medium text-slate-700">
            {status === 'checking' && 'Checking backend connection…'}
            {status === 'connected' && 'Backend connected'}
            {status === 'error' && 'Backend unreachable'}
          </span>
        </div>

        {status === 'connected' && detail && (
          <pre className="mt-4 text-xs bg-slate-900 text-slate-100 rounded-lg p-3 overflow-x-auto">
            {JSON.stringify(detail, null, 2)}
          </pre>
        )}

        {status === 'error' && (
          <p className="mt-4 text-sm text-red-600">{error}</p>
        )}
      </div>
    </div>
  )
}

export default App
