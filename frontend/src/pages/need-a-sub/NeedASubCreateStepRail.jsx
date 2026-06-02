import { createSubPostSteps } from './needASubCreateSteps.js'

export function NeedASubCreateStepRail({ activeStep }) {
  return (
    <ol className="need-sub-create-steps" aria-label="Create Sub Post progress">
      {createSubPostSteps.map((step, index) => {
        const stepNumber = index + 1
        const isActive = index === activeStep
        const isComplete = index < activeStep

        return (
          <li
            className={`need-sub-create-step ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''}`.trim()}
            key={step.key}
          >
            <span className="need-sub-create-step__content">
              <span className="need-sub-create-step__marker">{stepNumber}</span>
              <strong>
                <span className="need-sub-create-step__label-full">{step.label}</span>
                <span className="need-sub-create-step__label-mobile">{step.mobileLabel || step.label}</span>
              </strong>
            </span>
          </li>
        )
      })}
    </ol>
  )
}
