import { DEMO_SCENARIOS, getNextDemoStep, type DemoScenario } from './demoMode.js'

export type DemoLauncherState = {
  scenarioId: string | null
  stepIndex: number
  complete: boolean
}

export function createInitialDemoLauncherState(): DemoLauncherState {
  return { scenarioId: null, stepIndex: 0, complete: false }
}

export function getDefaultDemoScenario(): DemoScenario | null {
  return DEMO_SCENARIOS[0] ?? null
}

export function getActiveDemoScenario(state: DemoLauncherState): DemoScenario | null {
  return DEMO_SCENARIOS.find((scenario) => scenario.id === state.scenarioId) ?? null
}

export function startDemoLauncher(defaultScenario: DemoScenario | null): DemoLauncherState {
  if (!defaultScenario) return createInitialDemoLauncherState()
  return { scenarioId: defaultScenario.id, stepIndex: 0, complete: false }
}

export function resetDemoLauncher(
  state: DemoLauncherState,
  defaultScenario: DemoScenario | null,
): DemoLauncherState {
  if (!state.scenarioId) {
    return startDemoLauncher(defaultScenario)
  }
  return { ...state, stepIndex: 0, complete: false }
}

export function exitDemoLauncher(): DemoLauncherState {
  return createInitialDemoLauncherState()
}

export function selectDemoPrompt(
  defaultScenario: DemoScenario | null,
  index: number,
): DemoLauncherState {
  if (!defaultScenario) return createInitialDemoLauncherState()
  return { scenarioId: defaultScenario.id, stepIndex: index, complete: false }
}

export function advanceDemoLauncher(
  state: DemoLauncherState,
  prompt: string,
  activeScenario: DemoScenario | null,
): { nextState: DemoLauncherState; nextPrompt: string | null } {
  if (!activeScenario) {
    return { nextState: state, nextPrompt: null }
  }

  const currentPrompt = activeScenario.prompts[state.stepIndex] ?? ''
  if (prompt !== currentPrompt) {
    return { nextState: state, nextPrompt: null }
  }

  const nextStep = getNextDemoStep(state.stepIndex, activeScenario.prompts)
  const isFinalStep = nextStep === state.stepIndex && state.stepIndex === activeScenario.prompts.length - 1
  return {
    nextState: { ...state, stepIndex: nextStep, complete: isFinalStep },
    nextPrompt: isFinalStep ? null : (activeScenario.prompts[nextStep] || ''),
  }
}
