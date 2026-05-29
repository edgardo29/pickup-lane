import { steps } from './createGameData.js'

export function StepRail({ activeStep }) {
  return (
    <ol className="create-game-steps" aria-label="Create game progress">
      {steps.map((step) => (
        <li
          className={`create-game-step ${step.id === activeStep ? 'active' : step.id < activeStep ? 'complete' : ''}`.trim()}
          key={step.id}
        >
          <span className="create-game-step__content">
            <span className="create-game-step__marker">{step.id}</span>
            <strong>{step.label}</strong>
          </span>
        </li>
      ))}
    </ol>
  )
}
