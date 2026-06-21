import { useCallback, useMemo, useState } from 'react'
import {
  advanceDemoLauncher,
  createInitialDemoLauncherState,
  exitDemoLauncher,
  getActiveDemoScenario,
  getDefaultDemoScenario,
  resetDemoLauncher,
  selectDemoPrompt as selectDemoPromptState,
  startDemoLauncher,
} from './demoLauncherState.js'

export function useDemoLauncher() {
  const [state, setState] = useState(createInitialDemoLauncherState)

  const defaultDemoScenario = useMemo(() => getDefaultDemoScenario(), [])
  const activeDemoScenario = useMemo(() => getActiveDemoScenario(state), [state])
  const currentPrompt = activeDemoScenario?.prompts[state.stepIndex] ?? ''

  const startDemoMode = useCallback(() => {
    const nextState = startDemoLauncher(defaultDemoScenario)
    setState(nextState)
    return defaultDemoScenario?.prompts[0] || ''
  }, [defaultDemoScenario])

  const resetDemoMode = useCallback(() => {
    const nextState = resetDemoLauncher(state, defaultDemoScenario)
    setState(nextState)
    const scenario = getActiveDemoScenario(nextState) ?? defaultDemoScenario
    return scenario?.prompts[0] || ''
  }, [defaultDemoScenario, state])

  const exitDemoMode = useCallback(() => {
    setState(exitDemoLauncher())
  }, [])

  const selectDemoPrompt = useCallback((prompt: string, index: number) => {
    const nextState = selectDemoPromptState(defaultDemoScenario, index)
    setState(nextState)
    return prompt
  }, [defaultDemoScenario])

  const advanceDemoStep = useCallback((prompt: string) => {
    const { nextState, nextPrompt } = advanceDemoLauncher(state, prompt, activeDemoScenario)
    if (nextState !== state) {
      setState(nextState)
    }
    return nextPrompt
  }, [activeDemoScenario, state])

    return {
      activeDemoScenario,
      currentPrompt,
      demoStepIndex: state.stepIndex,
      isDemoComplete: state.complete,
      defaultDemoScenario,
      startDemoMode,
      resetDemoMode,
      exitDemoMode,
    selectDemoPrompt,
    advanceDemoStep,
  }
}
