import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PencilIcon } from '../../../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import { useAuth } from '../../../../hooks/useAuth.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import '../../../../styles/admin/AdminOfficialGameCreate.css'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import AdminCreateOfficialGamePreview from '../create/AdminCreateOfficialGamePreview.jsx'
import AdminCreateOfficialGameScheduleStep from '../create/AdminCreateOfficialGameScheduleStep.jsx'
import AdminCreateOfficialGameStepRail from '../create/AdminCreateOfficialGameStepRail.jsx'
import {
  getAdminOfficialGame,
  updateAdminOfficialGame,
} from '../shared/adminOfficialGamesApi.js'
import AdminEditOfficialGameDetailsStep from './AdminEditOfficialGameDetailsStep.jsx'
import AdminEditOfficialGameReviewStep from './AdminEditOfficialGameReviewStep.jsx'
import {
  adminEditOfficialGameSteps,
  buildAdminOfficialEditForm,
  buildAdminOfficialEditPayload,
  validateAdminOfficialEditForm,
  validateAdminOfficialEditStep,
} from './adminEditOfficialGameData.js'

function AdminEditOfficialGameFlow({ gameId }) {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [activeStep, setActiveStep] = useState(1)
  const [game, setGame] = useState(null)
  const [form, setForm] = useState(() => buildAdminOfficialEditForm(null))
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [stepError, setStepError] = useState('')
  const [saveState, setSaveState] = useState('idle')

  useEffect(() => {
    if (!currentUser) {
      return undefined
    }

    let isMounted = true

    async function loadGame() {
      setLoadState('loading')
      setPageError('')
      setStepError('')

      try {
        const response = await getAdminOfficialGame({
          firebaseUser: currentUser,
          gameId,
        })
        if (!isMounted) {
          return
        }

        setGame(response.game)
        setForm(buildAdminOfficialEditForm(response.game))
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setPageError(error.message || 'Official game could not be loaded.')
        setLoadState('error')
      }
    }

    loadGame()

    return () => {
      isMounted = false
    }
  }, [currentUser, gameId])

  function updateField(field, value) {
    setPageError('')
    setStepError('')
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
  }

  function exitToGame() {
    navigate(`/admin/official-games/${gameId}`)
  }

  function goNext() {
    const error = validateAdminOfficialEditStep(activeStep, form)
    if (error) {
      setStepError(error)
      return
    }

    setActiveStep((step) => Math.min(step + 1, adminEditOfficialGameSteps.length))
  }

  function goBack() {
    setStepError('')
    setActiveStep((step) => Math.max(step - 1, 1))
  }

  async function handleSaveGame() {
    const validationError = validateAdminOfficialEditForm(form)
    if (validationError) {
      setActiveStep(validationError.step)
      setStepError(validationError.message)
      return
    }

    setSaveState('saving')
    setPageError('')
    setStepError('')

    try {
      await updateAdminOfficialGame({
        firebaseUser: currentUser,
        gameId,
        payload: buildAdminOfficialEditPayload(form),
      })
      navigate(`/admin/official-games/${gameId}`)
    } catch (error) {
      setPageError(error.message || 'Official game could not be updated.')
      setSaveState('idle')
    }
  }

  const isLastStep = activeStep === adminEditOfficialGameSteps.length
  const isSaving = saveState === 'saving'

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Games', 'Official Games']}
      description="Update the game setup, booking controls, and player notes."
      icon={PencilIcon}
      title="Edit Official Game"
    >
      {loadState === 'loading' && (
        <p className="admin-official-empty">Loading game.</p>
      )}

      {loadState === 'error' && (
        <FormErrorMessage>{pageError}</FormErrorMessage>
      )}

      {loadState === 'ready' && game?.id === gameId && (
        <div className="admin-create-flow admin-edit-official-flow">
          <AdminCreateOfficialGameStepRail
            activeStep={activeStep}
            ariaLabel="Edit official game progress"
            steps={adminEditOfficialGameSteps}
          />

          <section className="admin-create-layout">
            <div className="admin-create-panel">
              {activeStep !== 3 && <FormErrorMessage>{pageError}</FormErrorMessage>}

              {activeStep === 1 && (
                <AdminCreateOfficialGameScheduleStep
                  form={form}
                  headingText="Update schedule, group, skill, environment, capacity, and price."
                  headingTitle="Game setup"
                  updateField={updateField}
                />
              )}
              {activeStep === 2 && (
                <AdminEditOfficialGameDetailsStep form={form} updateField={updateField} />
              )}
              {activeStep === 3 && (
                <AdminEditOfficialGameReviewStep form={form} saveError={pageError} />
              )}

              <FormErrorMessage>{stepError}</FormErrorMessage>

              <div className="admin-create-actions">
                <button className="admin-create-secondary" type="button" onClick={exitToGame}>
                  Back to game
                </button>
                <div className="admin-create-actions__right">
                  {activeStep > 1 && (
                    <button className="admin-create-secondary" type="button" onClick={goBack}>
                      Back
                    </button>
                  )}
                  {isLastStep ? (
                    <button
                      className="admin-create-primary admin-create-primary--publish"
                      disabled={isSaving}
                      type="button"
                      onClick={handleSaveGame}
                    >
                      <span>{isSaving ? 'Saving changes...' : 'Save changes'}</span>
                    </button>
                  ) : (
                    <button className="admin-create-primary" type="button" onClick={goNext}>
                      <span className="admin-create-primary__label-full">
                        Next: {adminEditOfficialGameSteps[activeStep].label}
                      </span>
                      <span className="admin-create-primary__label-short">Next</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            <AdminCreateOfficialGamePreview activeStep={activeStep} form={form} />
          </section>
        </div>
      )}
    </AdminWorkspaceLayout>
  )
}

function AdminEditOfficialGamePage() {
  const { gameId } = useParams()

  return <AdminEditOfficialGameFlow gameId={gameId} key={gameId} />
}

export default AdminEditOfficialGamePage
