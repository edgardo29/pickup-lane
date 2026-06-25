import { BadgePlus } from 'lucide-react'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import AdminCreateOfficialGamePreview from './AdminCreateOfficialGamePreview.jsx'
import AdminCreateOfficialGameReviewStep from './AdminCreateOfficialGameReviewStep.jsx'
import AdminCreateOfficialGameRulesStep from './AdminCreateOfficialGameRulesStep.jsx'
import AdminCreateOfficialGameScheduleStep from './AdminCreateOfficialGameScheduleStep.jsx'
import AdminCreateOfficialGameStepRail from './AdminCreateOfficialGameStepRail.jsx'
import AdminCreateOfficialGameVenueStep from './AdminCreateOfficialGameVenueStep.jsx'
import { adminCreateOfficialGameSteps } from './adminCreateOfficialGameData.js'

function AdminCreateOfficialGameLayout({
  activeStep,
  form,
  hasCreatedGame,
  onBack,
  onCancel,
  onCreate,
  onNext,
  onPhotoAdd,
  onPhotoRemove,
  onRetryReplacementSource,
  onUpdateField,
  pageError,
  photoError,
  photos,
  replacementLoadState,
  replacementSourceGame,
  saveState,
  stepError,
}) {
  const isLastStep = activeStep === adminCreateOfficialGameSteps.length
  const replacementSourceBlocked = (
    replacementLoadState === 'loading'
    || replacementLoadState === 'error'
  )

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Games', 'Create Official Game']}
        description="Configure and publish a new Pickup Lane official game."
        icon={BadgePlus}
        title="Create Official Game"
      >
        <div className="admin-create-flow">
          <AdminCreateOfficialGameStepRail activeStep={activeStep} />

          <section className="admin-create-layout">
            <div className="admin-create-panel">
              {replacementSourceGame && (
                <div className="admin-create-replacement-note" role="status">
                  <strong>Replacement source</strong>
                  <span>
                    {replacementSourceGame.title || 'Official game'} · {formatReplacementSourceSchedule(replacementSourceGame)}
                  </span>
                </div>
              )}

              {replacementLoadState === 'loading' && (
                <div className="admin-create-replacement-note" role="status">
                  <strong>Replacement source</strong>
                  <span>Loading source game...</span>
                </div>
              )}

              {replacementLoadState === 'error' && (
                <div className="admin-create-replacement-error">
                  <FormErrorMessage>{pageError}</FormErrorMessage>
                  <button
                    className="admin-create-secondary"
                    type="button"
                    onClick={onRetryReplacementSource}
                  >
                    Try again
                  </button>
                </div>
              )}

              {!replacementSourceBlocked && (
                <>
                  {activeStep !== 4 && <FormErrorMessage>{pageError}</FormErrorMessage>}

                  {activeStep === 1 && (
                    <AdminCreateOfficialGameScheduleStep form={form} updateField={onUpdateField} />
                  )}
                  {activeStep === 2 && (
                    <AdminCreateOfficialGameVenueStep
                      form={form}
                      photoError={photoError}
                      photos={photos}
                      updateField={onUpdateField}
                      onPhotoAdd={onPhotoAdd}
                      onPhotoRemove={onPhotoRemove}
                    />
                  )}
                  {activeStep === 3 && (
                    <AdminCreateOfficialGameRulesStep form={form} updateField={onUpdateField} />
                  )}
                  {activeStep === 4 && (
                    <AdminCreateOfficialGameReviewStep
                      form={form}
                      photos={photos}
                      publishError={pageError}
                    />
                  )}

                  <FormErrorMessage>{stepError}</FormErrorMessage>
                </>
              )}

              <div className="admin-create-actions">
                <button className="admin-create-cancel" type="button" onClick={onCancel}>
                  Cancel
                </button>
                {!replacementSourceBlocked && (
                  <div className="admin-create-actions__right">
                    {activeStep > 1 && (
                      <button className="admin-create-secondary" type="button" onClick={onBack}>
                        Back
                      </button>
                    )}
                    {isLastStep ? (
                      <button
                        className="admin-create-primary admin-create-primary--publish"
                        disabled={
                          saveState === 'checking_photos' ||
                            saveState === 'saving' ||
                            saveState === 'uploading'
                        }
                        type="button"
                        onClick={onCreate}
                      >
                        <span>{getCreateButtonLabel(saveState, hasCreatedGame)}</span>
                        <span aria-hidden="true">→</span>
                      </button>
                    ) : (
                      <button className="admin-create-primary" type="button" onClick={onNext}>
                        <span className="admin-create-primary__label-full">
                          Next: {adminCreateOfficialGameSteps[activeStep].label}
                        </span>
                        <span className="admin-create-primary__label-short">Next</span>
                        <span aria-hidden="true">→</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {!replacementSourceBlocked && (
              <AdminCreateOfficialGamePreview activeStep={activeStep} form={form} />
            )}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

function formatReplacementSourceSchedule(game) {
  if (!game?.starts_at) {
    return 'Schedule unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: game.timezone || 'America/Chicago',
  }).format(new Date(game.starts_at))
}

function getCreateButtonLabel(saveState, hasCreatedGame) {
  if (saveState === 'saving') {
    return 'Creating Game...'
  }

  if (saveState === 'checking_photos') {
    return 'Creating Game...'
  }

  if (saveState === 'uploading') {
    return 'Creating Game...'
  }

  if (saveState === 'created' || hasCreatedGame) {
    return 'View Created Game'
  }

  return 'Create Official Game'
}

export default AdminCreateOfficialGameLayout
