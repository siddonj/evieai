import test from 'node:test'
import assert from 'node:assert/strict'

const demoMode = await import('./demoMode.js')
const { DEMO_SCENARIOS, getNextDemoStep } = demoMode
const prompts = [
  'Show me portfolio performance for this account.',
  'What open work orders need attention right now?',
  'Export this answer to PDF and Excel.',
]

test('defines a product-demo scenario for multi-source chat with export', () => {
  assert.equal(DEMO_SCENARIOS[0].id, 'multi-source-chat-export')
  assert.equal(DEMO_SCENARIOS[0].title, 'Multi-source chat with export')
  assert.deepEqual(DEMO_SCENARIOS[0].prompts, prompts)
})

test('advances through the guided sequence one step at a time', () => {
  assert.equal(getNextDemoStep(0, prompts), 1)
  assert.equal(getNextDemoStep(1, prompts), 2)
  assert.equal(getNextDemoStep(2, prompts), 2)
})
