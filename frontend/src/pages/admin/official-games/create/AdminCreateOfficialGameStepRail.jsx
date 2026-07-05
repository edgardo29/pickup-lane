import { adminCreateOfficialGameSteps } from './adminCreateOfficialGameData.js'

function AdminCreateOfficialGameStepRail({
  activeStep,
  ariaLabel = 'Create official game progress',
  steps = adminCreateOfficialGameSteps,
}) {
  return (
    <ol className="admin-create-steps" aria-label={ariaLabel}>
      {steps.map((step) => (
        <li
          className={`admin-create-step ${step.id === activeStep ? 'active' : step.id < activeStep ? 'complete' : ''}`.trim()}
          key={step.id}
        >
          <span className="admin-create-step__content">
            <span className="admin-create-step__marker">{step.id}</span>
            <strong>
              <span className="admin-create-step__label-full">{step.label}</span>
              <span className="admin-create-step__label-mobile">{step.mobileLabel || step.label}</span>
            </strong>
          </span>
        </li>
      ))}
    </ol>
  )
}

export default AdminCreateOfficialGameStepRail
