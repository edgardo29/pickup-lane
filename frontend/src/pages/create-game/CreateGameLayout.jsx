import { ArrowLeftIcon } from '../../components/AuthIcons.jsx'
import { AppPageHeader, AppPageShell } from '../../components/app/index.js'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { DiscardModal } from './CreateGameControls.jsx'
import { EmailVerificationBlocker } from './CreateGameEmailVerification.jsx'
import { CreateGamePreview } from './CreateGamePreview.jsx'
import { CreateGameSkeleton } from './CreateGameSkeleton.jsx'
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
    <AppPageShell className="create-game-page" mainClassName="create-game-shell">
        {isWaitingForUser ? (
          <CreateGameSkeleton isEditMode={isEditMode} />
        ) : (
          <>
            <AppPageHeader
              title={isEditMode ? 'Edit Game' : 'Create Game'}
              subtitle={
                isEditMode
                  ? 'Update your community game details.'
                  : 'Post a community game for players to join.'
              }
              actions={
                isEditMode ? (
                  <button className="create-game-header-back" type="button" onClick={onBack} aria-label="Go back">
                    <ArrowLeftIcon />
                  </button>
                ) : null
              }
            />

            <StepRail activeStep={activeStep} />

            <FormErrorMessage>{loadError}</FormErrorMessage>

            {shouldBlockForEmailVerification ? (
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

                  <FormErrorMessage>{stepError}</FormErrorMessage>

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
                          <span className="create-game-primary__label-full">Next: {steps[activeStep].label}</span>
                          <span className="create-game-primary__label-short">Next</span>
                          <span aria-hidden="true">→</span>
                        </button>
                      ) : (
                        <button
                          className="create-game-primary create-game-primary--publish"
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
                  activeStep={activeStep}
                  firstPublishIsFree={firstPublishIsFree}
                  form={form}
                  review={review}
                />
              </section>
            ) : null}
          </>
        )}

      {showDiscardModal && (
        <DiscardModal onClose={onCloseDiscard} onDiscard={onDiscard} />
      )}
    </AppPageShell>
  )
}
