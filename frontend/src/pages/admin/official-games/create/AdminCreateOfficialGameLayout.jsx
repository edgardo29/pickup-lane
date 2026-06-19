import { AppPageHeader, AppPageShell } from '../../../../components/app/index.js'
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
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-official-shell">
      <AppPageHeader
        subtitle="Admin"
        title="Create Official Game"
      />

      <AdminWorkspaceLayout>
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
                <div className="admin-create-replacement-error" role="alert">
                  <p className="admin-create-error admin-create-error--top">{pageError}</p>
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
                  {pageError && <p className="admin-create-error admin-create-error--top">{pageError}</p>}

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
                      publishError={pageError}
                    />
                  )}

                  {stepError && <p className="admin-create-error">{stepError}</p>}
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
                        className="admin-create-primary"
                        disabled={
                          saveState === 'checking_photos' ||
                            saveState === 'saving' ||
                            saveState === 'uploading'
                        }
                        type="button"
                        onClick={onCreate}
                      >
                        {getCreateButtonLabel(saveState, hasCreatedGame)}
                        <span aria-hidden="true">-&gt;</span>
                      </button>
                    ) : (
                      <button className="admin-create-primary" type="button" onClick={onNext}>
                        Next: {adminCreateOfficialGameSteps[activeStep].label}
                        <span aria-hidden="true">-&gt;</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {!replacementSourceBlocked && <AdminCreateOfficialGamePreview form={form} />}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
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
