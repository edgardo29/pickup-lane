import { adminCreateOfficialGameSteps } from './adminCreateOfficialGameData.js'

function AdminCreateOfficialGameStepRail({ activeStep }) {
  return (
    <ol className="admin-create-steps" aria-label="Create official game progress">
      {adminCreateOfficialGameSteps.map((step) => (
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
