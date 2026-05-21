import { steps } from './createGameData.js'

export function StepRail({ activeStep }) {
  return (
    <ol className="create-game-steps" aria-label="Create game progress">
      {steps.map((step) => (
        <li
          className={step.id === activeStep ? 'active' : step.id < activeStep ? 'complete' : ''}
          key={step.id}
        >
          <span>{step.id}</span>
          <strong>{step.label}</strong>
        </li>
      ))}
    </ol>
  )
}
