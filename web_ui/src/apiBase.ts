const LOCAL_ORCHESTRATOR_URL = 'http://localhost:8000'
const PRODUCTION_ORCHESTRATOR_URL = 'https://api.resiq.co'

export function getOrchestratorUrl(): string {
  const configured = import.meta.env.VITE_ORCHESTRATOR_URL?.trim()
  if (configured) {
    return configured.replace(/\/$/, '')
  }

  if (import.meta.env.DEV) {
    return LOCAL_ORCHESTRATOR_URL
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return LOCAL_ORCHESTRATOR_URL
    }
    if (hostname === 'demo.resiq.co') {
      return PRODUCTION_ORCHESTRATOR_URL
    }
  }

  return PRODUCTION_ORCHESTRATOR_URL
}
