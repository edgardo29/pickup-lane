import { ArrowLeftIcon } from '../../components/AuthIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import { DiscardModal } from './CreateGameControls.jsx'
import { EmailVerificationBlocker } from './CreateGameEmailVerification.jsx'
import { CreateGamePreview } from './CreateGamePreview.jsx'
import { BasicsStep, LocationStep, NotesStep, ReviewStep, StepRail } from './CreateGameSteps.jsx'
import { steps } from './createGameData.js'

export function CreateGameLayout({
  activeStep,
  currentUser,
  firstPublishIsFree,
  form,
  isEditMode,
  isWaitingForUser,
  loadError,
  onBack,
  onCancel,
  onCloseDiscard,
  onDiscard,
  onNext,
  onPublish,
  onSendVerification,
  onUpdateField,
  publishError,
  review,
  shouldBlockForEmailVerification,
  showDiscardModal,
  status,
  stepError,
  verificationCooldownSeconds,
  verificationError,
  verificationNotice,
  verificationStatus,
  visibleUser,
}) {
  return (
    <div className="create-game-page">
      <BrowseAppNav />

      <main className="create-game-shell">
        <header className={`create-game-topbar ${isEditMode ? '' : 'create-game-topbar--main'}`.trim()}>
          {isEditMode && (
            <button type="button" onClick={onBack} aria-label="Go back">
              <ArrowLeftIcon />
            </button>
          )}
          <div>
            <h1>{isEditMode ? 'Edit Game' : 'Create Game'}</h1>
            <p>
              {isEditMode
                ? 'Update your community game details.'
                : 'Post a community game for players to join.'}
            </p>
          </div>
        </header>

        <StepRail activeStep={activeStep} />

        {loadError && <p className="create-game-error">{loadError}</p>}

        {isWaitingForUser ? (
          <section className="create-game-blocker">
            <div>
              <p>Loading</p>
              <h2>Loading Create Game</h2>
              <span>One moment while your account loads.</span>
            </div>
          </section>
        ) : shouldBlockForEmailVerification ? (
          <EmailVerificationBlocker
            cooldownSeconds={verificationCooldownSeconds}
            error={verificationError}
            notice={verificationNotice}
            status={verificationStatus}
            onSend={onSendVerification}
          />
        ) : visibleUser ? (
          <section className="create-game-layout">
            <div className="create-game-panel">
              {activeStep === 1 && <BasicsStep form={form} updateField={onUpdateField} />}
              {activeStep === 2 && <LocationStep form={form} updateField={onUpdateField} />}
              {activeStep === 3 && <NotesStep form={form} updateField={onUpdateField} />}
              {activeStep === 4 && (
                <ReviewStep
                  firstPublishIsFree={firstPublishIsFree}
                  form={form}
                  isEditMode={isEditMode}
                  publishError={publishError}
                  review={review}
                />
              )}

              {stepError && <p className="create-game-error">{stepError}</p>}

              <div className="create-game-actions">
                <button className="create-game-cancel" type="button" onClick={onCancel}>
                  Cancel
                </button>
                <div className="create-game-actions__right">
                  {activeStep > 1 && (
                    <button className="create-game-secondary" type="button" onClick={onBack}>
                      Back
                    </button>
                  )}
                  {activeStep < steps.length ? (
                    <button className="create-game-primary" type="button" onClick={onNext}>
                      Next: {steps[activeStep].label}
                      <span aria-hidden="true">→</span>
                    </button>
                  ) : (
                    <button
                      className="create-game-primary"
                      disabled={!currentUser || status === 'publishing'}
                      type="button"
                      onClick={onPublish}
                    >
                      {status === 'publishing'
                        ? isEditMode
                          ? 'Saving...'
                          : 'Publishing...'
                        : isEditMode
                          ? 'Save Changes'
                          : 'Publish Game'}
                      <span aria-hidden="true">→</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            <CreateGamePreview
              firstPublishIsFree={firstPublishIsFree}
              form={form}
              review={review}
            />
          </section>
        ) : null}
      </main>

      {showDiscardModal && (
        <DiscardModal onClose={onCloseDiscard} onDiscard={onDiscard} />
      )}
    </div>
  )
}
