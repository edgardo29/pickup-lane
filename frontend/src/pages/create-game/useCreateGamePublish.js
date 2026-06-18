import { useState } from 'react'
import {
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

      const game = await publishCommunityGame(
        firebaseUser,
        buildCommunityPublishPayload(form, paymentMethod),
      )

      setCreatedGameId(game.id)
      setStatus('published')
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
