import { adminCreateOfficialGameSteps } from './adminCreateOfficialGameData.js'

function AdminCreateOfficialGameStepRail({ activeStep }) {
  return (
    <ol className="admin-create-steps" aria-label="Create official game progress">
      {adminCreateOfficialGameSteps.map((step) => (
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

export default AdminCreateOfficialGameStepRail
