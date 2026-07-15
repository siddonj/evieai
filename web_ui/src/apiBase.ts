const LOCAL_ORCHESTRATOR_URL = 'http://localhost:8000'
const PRODUCTION_ORCHESTRATOR_URL = 'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io'

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, '')
}

function isLocalHostname(hostname: string): boolean {
  return ['localhost', '127.0.0.1', '0.0.0.0', '::1'].includes(hostname) || hostname.endsWith('.local')
}

export function resolveOrchestratorUrl(options: {
  configured?: string
  hostname?: string
  isDev?: boolean
  currentOrigin?: string
}): string {
  const hostname = (options.hostname || '').toLowerCase()
  if (hostname && isLocalHostname(hostname)) {
    return LOCAL_ORCHESTRATOR_URL
  }

  const configured = options.configured?.trim()
  if (options.currentOrigin) {
    try {
      const configuredUrl = new URL(configured || '')
      if (configured && configuredUrl.origin !== options.currentOrigin) {
        if (hostname === 'demo.resiq.co' || hostname.endsWith('.resiq.co')) {
          return PRODUCTION_ORCHESTRATOR_URL
        }
        return options.currentOrigin
      }
    } catch {
      // Fall back to the current origin if the configured URL is malformed.
    }
  }

  if (configured) {
    return normalizeBaseUrl(configured)
  }

  if (options.isDev) {
    return LOCAL_ORCHESTRATOR_URL
  }

  if (hostname === 'demo.resiq.co' || hostname.endsWith('.resiq.co')) {
    return PRODUCTION_ORCHESTRATOR_URL
  }

  if (options.currentOrigin) {
    return options.currentOrigin
  }

  return PRODUCTION_ORCHESTRATOR_URL
}

export function getOrchestratorUrl(): string {
  const currentOrigin = typeof window !== 'undefined' ? window.location.origin : ''
  const hostname = typeof window !== 'undefined' ? window.location.hostname : ''

  return resolveOrchestratorUrl({
    configured: import.meta.env.VITE_ORCHESTRATOR_URL,
    hostname,
    isDev: import.meta.env.DEV,
    currentOrigin,
  })
}
