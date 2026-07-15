import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveOrchestratorUrl } from './apiBase'

test('uses local backend for localhost hosts', () => {
  assert.equal(
    resolveOrchestratorUrl({ hostname: 'localhost', currentOrigin: 'http://localhost:5173' }),
    'http://localhost:8000'
  )
})

test('uses current origin when configured URL points elsewhere', () => {
  assert.equal(
    resolveOrchestratorUrl({
      configured: 'https://api.resiq.co',
      hostname: 'example.com',
      currentOrigin: 'https://example.com',
    }),
    'https://example.com'
  )
})

test('falls back to configured URL when it matches host', () => {
  assert.equal(
    resolveOrchestratorUrl({
      configured: 'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io',
      hostname: 'example.com',
      currentOrigin: 'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io',
    }),
    'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io'
  )
})

test('uses the production API for demo.resiq.co', () => {
  assert.equal(
    resolveOrchestratorUrl({
      configured: 'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io',
      hostname: 'demo.resiq.co',
      currentOrigin: 'https://demo.resiq.co',
    }),
    'https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io'
  )
})
