export type DemoScenario = {
  id: string
  title: string
  description: string
  prompts: string[]
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'multi-source-chat-export',
    title: 'Multi-source chat with export',
    description: 'A guided product demo that shows routing, grounded answers, and export.',
    prompts: [
      'Show me portfolio performance for this account.',
      'What open work orders need attention right now?',
      'Export this answer to PDF and Excel.',
    ],
  },
]

export function getNextDemoStep(stepIndex: number, prompts: string[]): number {
  return Math.min(stepIndex + 1, Math.max(0, prompts.length - 1))
}
