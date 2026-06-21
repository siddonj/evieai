import test from 'node:test'
import assert from 'node:assert/strict'
import { DEMO_SCENARIOS } from './demoMode.js'
import {
  advanceDemoLauncher,
  createInitialDemoLauncherState,
  exitDemoLauncher,
  getActiveDemoScenario,
  getDefaultDemoScenario,
  resetDemoLauncher,
  selectDemoPrompt,
  startDemoLauncher,
} from './demoLauncherState.js'

const defaultScenario = DEMO_SCENARIOS[0] || null

test('starts and exits the demo launcher cleanly', () => {
  const started = startDemoLauncher(defaultScenario)
  assert.equal(started.scenarioId, defaultScenario?.id || null)
  assert.equal(started.stepIndex, 0)
  assert.equal(started.complete, false)
  assert.deepEqual(exitDemoLauncher(), createInitialDemoLauncherState())
})

test('resets the demo launcher to the first step', () => {
  const started = startDemoLauncher(defaultScenario)
  const reset = resetDemoLauncher({ ...started, stepIndex: 2 }, defaultScenario)
  assert.equal(reset.scenarioId, started.scenarioId)
  assert.equal(reset.stepIndex, 0)
  assert.equal(reset.complete, false)
})

test('selects and advances guided prompts', () => {
  const selected = selectDemoPrompt(defaultScenario, 1)
  const activeScenario = getActiveDemoScenario(selected)
  assert.equal(activeScenario?.id, defaultScenario?.id)

  const advanced = advanceDemoLauncher(selected, defaultScenario?.prompts[1] || '', activeScenario)
  assert.equal(advanced.nextState.stepIndex, 2)
  assert.equal(advanced.nextPrompt, defaultScenario?.prompts[2] || '')
})

test('marks the flow complete at the last step', () => {
  const selected = selectDemoPrompt(defaultScenario, 2)
  const activeScenario = getActiveDemoScenario(selected)
  const advanced = advanceDemoLauncher(selected, defaultScenario?.prompts[2] || '', activeScenario)
  assert.equal(advanced.nextState.complete, true)
  assert.equal(advanced.nextPrompt, null)
})

test('returns the default scenario from helper', () => {
  assert.equal(getDefaultDemoScenario()?.id, defaultScenario?.id)
})
