import { useState } from 'react'
import {
  getCommunityPublishAttempt,
  patchHostEditGame,
  publishCommunityGame,
  upsertHostCommunityGameDetails,
} from './createGameApi.js'
import {
  buildCommunityGameDetailPayload,
  buildCommunityPublishPayload,
  buildHostEditPayload,
} from './createGamePayloads.js'
import { validateCreateGame } from './createGameValidation.js'
import { stripePromise } from '../../lib/stripe.js'

const PUBLISH_ATTEMPT_POLL_COUNT = 12
const PUBLISH_ATTEMPT_POLL_DELAY_MS = 1200

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

export function useCreateGamePublish({
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
}) {
  const [status, setStatus] = useState('idle')
  const [publishError, setPublishError] = useState('')
  const [stepError, setStepError] = useState('')

  function clearPublishFeedback() {
    setStepError('')
    setPublishError('')
  }

  async function pollPublishAttempt(attemptId) {
    for (let attempt = 0; attempt < PUBLISH_ATTEMPT_POLL_COUNT; attempt += 1) {
      const latestStatus = await getCommunityPublishAttempt(firebaseUser, attemptId)

      if (latestStatus.status === 'published' && latestStatus.created_game_id) {
        setCreatedGameId(latestStatus.created_game_id)
        setStatus('published')
        return latestStatus
      }

      if (latestStatus.status === 'failed') {
        throw new Error(
          latestStatus.error_message || 'Publish fee payment could not be confirmed.',
        )
      }

      await wait(PUBLISH_ATTEMPT_POLL_DELAY_MS)
    }

    throw new Error('Your publish fee is still confirming. Please check again shortly.')
  }

  async function handlePublishResult(result) {
    if (result.status === 'published' && result.game?.id) {
      setCreatedGameId(result.game.id)
      setStatus('published')
      return
    }

    if (!result.attempt_id) {
      throw new Error(result.error_message || 'Unable to publish game.')
    }

    if (result.status === 'failed') {
      throw new Error(result.error_message || 'Publish fee payment could not be confirmed.')
    }

    if (result.status === 'requires_action') {
      if (!result.client_secret) {
        throw new Error('Secure payment authentication could not be started.')
      }

      const stripe = await stripePromise
      if (!stripe) {
        throw new Error('Secure payment is not ready. Please try again.')
      }

      const nextActionResult = await stripe.handleNextAction({
        clientSecret: result.client_secret,
      })
      if (nextActionResult.error) {
        throw new Error(
          nextActionResult.error.message || 'Payment authentication failed.',
        )
      }
    }

    await pollPublishAttempt(result.attempt_id)
  }

  async function submitGame() {
    if (!currentUser) {
      setPublishError('Demo user is not loaded yet.')
      return
    }

    if (!isEditMode && !isHostEmailVerified) {
      setPublishError('Verify your email before publishing.')
      return
    }

    const error = validateCreateGame(form)
    if (error) {
      setPublishError('')
      setStepError(error.message)
      setActiveStep(error.step)
      return
    }

    setStatus('publishing')
    setPublishError('')

    try {
      if (isEditMode) {
        await patchHostEditGame(firebaseUser, gameId, buildHostEditPayload(form))
        await upsertHostCommunityGameDetails(
          firebaseUser,
          gameId,
          buildCommunityGameDetailPayload(form),
        )

        navigate(`/games/${gameId}`)
        return
      }

      const publishResult = await publishCommunityGame(
        firebaseUser,
        buildCommunityPublishPayload(form, paymentMethod),
      )
      await handlePublishResult(publishResult)
    } catch (error) {
      setStatus('idle')
      setPublishError(error instanceof Error ? error.message : 'Unable to publish game.')
    }
  }

  return {
    clearPublishFeedback,
    publishError,
    setStepError,
    status,
    stepError,
    submitGame,
  }
}
