import { useState } from 'react'
import {
  patchJson,
  postJson,
  publishCommunityGame,
} from './createGameApi.js'
import {
  buildCommunityGameDetailPayload,
  buildCommunityPublishPayload,
  buildHostEditPayload,
} from './createGamePayloads.js'
import { validateCreateGame } from './createGameValidation.js'

export function useCreateGamePublish({
  communityGameDetailId,
  currentUser,
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
        await patchJson(`/games/${gameId}/host-edit`, buildHostEditPayload(form, currentUser))

        const communityGameDetailPayload = buildCommunityGameDetailPayload(form, gameId)
        if (communityGameDetailId) {
          await patchJson(
            `/community-game-details/${communityGameDetailId}`,
            communityGameDetailPayload,
          )
        } else {
          await postJson('/community-game-details', communityGameDetailPayload)
        }

        navigate(`/games/${gameId}`)
        return
      }

      const game = await publishCommunityGame(
        buildCommunityPublishPayload(form, currentUser, paymentMethod),
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
