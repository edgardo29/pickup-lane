import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/create-game/CreateGamePage.css'
import { CreateGameLayout } from './CreateGameLayout.jsx'
import { PublishedState } from './CreateGamePreview.jsx'
import {
  createGameFieldLimits,
  steps,
} from './createGameData.js'
import { buildReview } from './createGameFormatters.js'
import { validateStep } from './createGameValidation.js'
import { useCreateGameContext } from './useCreateGameContext.js'
import { useCreateGameEmailVerification } from './useCreateGameEmailVerification.js'
import { useCreateGamePublish } from './useCreateGamePublish.js'

function CreateGamePage() {
  const navigate = useNavigate()
  const { gameId } = useParams()
  const {
    appUser,
    currentUser: firebaseUser,
    isLoading,
    refreshCurrentUserVerification,
    sendCurrentUserVerificationEmail,
  } = useAuth()
  const isEditMode = Boolean(gameId)
  const [activeStep, setActiveStep] = useState(1)
  const [showDiscardModal, setShowDiscardModal] = useState(false)
  const {
    resetVerificationState,
    sendEmailVerificationLink,
    verificationCooldownSeconds,
    verificationError,
    verificationNotice,
    verificationStatus,
  } = useCreateGameEmailVerification({
    appUser,
    isEditMode,
    refreshCurrentUserVerification,
    sendCurrentUserVerificationEmail,
  })
  const {
    createdGameId,
    currentUser,
    firstPublishIsFree,
    form,
    formBaseline,
    isContextLoading,
    loadError,
    paymentMethod,
    setCreatedGameId,
    setForm,
  } = useCreateGameContext({
    appUser,
    firebaseUser,
    gameId,
    isEditMode,
    isLoading,
    onVerifiedHostRefresh: resetVerificationState,
    refreshCurrentUserVerification,
  })
  const visibleUser = currentUser || appUser
  const isVerifiedContextPending = Boolean(
    appUser?.id && !currentUser && !loadError && (isEditMode || appUser.email_verified_at),
  )
  const isWaitingForUser = (
    (isLoading && !visibleUser) ||
    (isContextLoading && !loadError) ||
    isVerifiedContextPending
  )
  const isHostEmailVerified = Boolean(visibleUser?.email_verified_at)
  const shouldBlockForEmailVerification = visibleUser && !isEditMode && !isHostEmailVerified
  const {
    clearPublishFeedback,
    publishError,
    setStepError,
    status,
    stepError,
    submitGame,
  } = useCreateGamePublish({
    currentUser,
    firebaseUser,
    form,
    gameId,
    isEditMode,
    isHostEmailVerified,
    navigate,
    paymentMethod,
    setActiveStep,
    setCreatedGameId,
  })

  const review = useMemo(() => buildReview(form), [form])
  const hasUnsavedChanges = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(formBaseline),
    [form, formBaseline],
  )
  function updateField(field, value) {
    clearPublishFeedback()
    const limit = createGameFieldLimits[field]
    const nextValue = typeof value === 'string' && limit ? value.slice(0, limit) : value
    setForm((currentForm) => ({ ...currentForm, [field]: nextValue }))
  }

  function goNext() {
    const error = validateStep(activeStep, form)
    if (error) {
      setStepError(error)
      return
    }

    clearPublishFeedback()
    setActiveStep((step) => Math.min(step + 1, steps.length))
  }

  function goBack() {
    if (activeStep > 1) {
      clearPublishFeedback()
      setActiveStep((step) => step - 1)
      return
    }

    requestCancel()
  }

  function requestCancel() {
    if (hasUnsavedChanges) {
      setShowDiscardModal(true)
      return
    }

    navigate(getExitPath(isEditMode, gameId))
  }

  function discardGame() {
    setShowDiscardModal(false)
    navigate(getExitPath(isEditMode, gameId))
  }

  if (status === 'published') {
    return <PublishedState gameId={createdGameId} />
  }

  return (
    <CreateGameLayout
      activeStep={activeStep}
      currentUser={currentUser}
      firstPublishIsFree={firstPublishIsFree}
      form={form}
      isEditMode={isEditMode}
      isWaitingForUser={isWaitingForUser}
      loadError={loadError}
      onBack={goBack}
      onCancel={requestCancel}
      onCloseDiscard={() => setShowDiscardModal(false)}
      onDiscard={discardGame}
      onNext={goNext}
      onPublish={submitGame}
      onSendVerification={sendEmailVerificationLink}
      onUpdateField={updateField}
      publishError={publishError}
      review={review}
      shouldBlockForEmailVerification={shouldBlockForEmailVerification}
      showDiscardModal={showDiscardModal}
      status={status}
      stepError={stepError}
      verificationCooldownSeconds={verificationCooldownSeconds}
      verificationError={verificationError}
      verificationNotice={verificationNotice}
      verificationStatus={verificationStatus}
      visibleUser={visibleUser}
    />
  )

}

function getExitPath(isEditMode, gameId) {
  return isEditMode && gameId ? `/games/${gameId}` : '/games'
}

export default CreateGamePage
